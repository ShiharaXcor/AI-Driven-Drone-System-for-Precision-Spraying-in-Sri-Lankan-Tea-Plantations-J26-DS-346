"""Component 2 - live loop for the PX4 + Gazebo simulator.

Every second it:
  1. reads the drone's heading, height, roll and position from PX4 (MAVLink, port 14540),
  2. knows the wind (fixed from the world file, or changed step by step with --timeline / --move),
  3. runs recommend() - the same C2 code as the backend,
  4. with --move: sends C2's path offset to PX4, so the drone really moves sideways,
  5. prints the result and saves it to a CSV file in simulation/logs/.

Run (WSL Ubuntu, simulator already running, venv active, from the repo root):
    python simulation/c2_live.py --world c2_windy              # fixed wind from the world file
    python simulation/c2_live.py --world c2_windy --timeline   # calm -> moderate -> strong -> moderate
    python simulation/c2_live.py --world c2_windy --move       # crosswind test: the drone moves sideways
Stop with Ctrl + C.
"""
import argparse
import csv
import math
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from pymavlink import mavutil

HERE = Path(__file__).resolve().parent          # .../simulation
REPO = HERE.parent                              # repo root
sys.path.insert(0, str(REPO / "backend"))
from src.components.c2_wind_handling.compensation.compensation import recommend  # noqa: E402

TEMP_C, RH_PCT = 28, 70        # fixed for the simulation (later: real BME280 readings)
MIN_HEIGHT_M = 2.0             # the model learned heights of 2.0-3.5 m
M_PER_DEG = 111_320            # metres per degree of latitude
RESEND_M = 0.1                 # only send a new position when the offset changes by more than this

# (stage name, wind toward EAST m/s, wind toward NORTH m/s, seconds)
TIMELINE = [
    ("calm",     0.3, 0.0, 60),
    ("moderate", 2.0, 1.0, 60),
    ("strong",   5.0, 2.0, 60),
    ("moderate", 2.0, 1.0, 60),
]

# --move: wind fully from the side, strong enough that the nozzle tilt hits 30 deg
# (the rest becomes a path offset), but below the 4.5 m/s safety limit.
MOVE_TIMELINE = [
    ("calm",      0.3, 0.0, 30),
    ("crosswind", 0.0, 3.0, 60),
    ("strong",    5.0, 2.0, 30),
    ("crosswind", 0.0, 3.0, 60),
]

COLUMNS = ["t_s", "stage", "heading_deg", "height_m", "roll_deg", "wind_ms", "wind_from_deg",
           "mode", "crosswind_ms", "wind_from_side", "drift_m", "drift_risk",
           "tilt_deg", "servo_deg", "path_offset_m", "path_offset_side",
           "offset_cmd_m", "side_pos_m"]


def to_speed_dir(east, north):
    """Gazebo wind arrow (toward east, toward north) -> (speed m/s, direction the wind comes FROM)."""
    speed = math.hypot(east, north)
    from_deg = (math.degrees(math.atan2(east, north)) + 180) % 360
    return speed, from_deg


def world_wind(world):
    """Read <linear_velocity> X Y Z from the world file in the repo."""
    sdf = (REPO / "simulation" / "gazebo" / "worlds" / f"{world}.sdf").read_text()
    match = re.search(r"<linear_velocity>([^<]+)</linear_velocity>", sdf)
    east, north, _ = (float(v) for v in match.group(1).split())
    return east, north


def set_wind(world, east, north):
    """Change the wind in the running Gazebo world (same as typing gz topic by hand)."""
    msg = f"linear_velocity: {{x: {east}, y: {north}, z: 0}}, enable_wind: true"
    subprocess.run(["gz", "topic", "-t", f"/world/{world}/wind", "-m", "gz.msgs.Wind", "-p", msg],
                   check=True, timeout=10)


def side_position(lat, lon, base_lat, base_lon, path_heading):
    """How far the drone is from the planned line, in metres (+ = right of the line)."""
    north = (lat - base_lat) * M_PER_DEG
    east = (lon - base_lon) * M_PER_DEG * math.cos(math.radians(base_lat))
    right = math.radians(path_heading + 90)
    return east * math.sin(right) + north * math.cos(right)


def offset_point(base_lat, base_lon, path_heading, offset_m):
    """GPS point that is offset_m to the right (+) or left (-) of the planned line."""
    right = math.radians(path_heading + 90)
    north = offset_m * math.cos(right)
    east = offset_m * math.sin(right)
    lat = base_lat + north / M_PER_DEG
    lon = base_lon + east / (M_PER_DEG * math.cos(math.radians(base_lat)))
    return lat, lon


def send_reposition(m, lat, lon):
    """Ask PX4 to fly to (lat, lon) and hold there, keeping the same height."""
    m.mav.command_int_send(
        m.target_system, m.target_component,
        mavutil.mavlink.MAV_FRAME_GLOBAL,
        mavutil.mavlink.MAV_CMD_DO_REPOSITION,
        0, 0,
        -1,                 # param1: default speed
        1,                  # param2: allow PX4 to switch to Hold mode
        0,                  # param3: unused
        float("nan"),       # param4: yaw - NaN = keep the current heading
        int(lat * 1e7), int(lon * 1e7),
        float("nan"),       # altitude - NaN = keep the current height
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--world", default="c2_windy",
                        help="the world the simulator is running: c2_calm, c2_windy or c2_strong")
    parser.add_argument("--timeline", action="store_true",
                        help="change the wind step by step: calm -> moderate -> strong -> moderate")
    parser.add_argument("--move", action="store_true",
                        help="crosswind test: send C2's path offset to PX4 so the drone moves sideways")
    args = parser.parse_args()

    if args.move:
        stages = MOVE_TIMELINE
    elif args.timeline:
        stages = TIMELINE
    else:
        east, north = world_wind(args.world)
        stages = [("fixed", east, north, None)]          # None = no time limit
    changes_wind = args.move or args.timeline

    log_dir = HERE / "logs"
    log_dir.mkdir(exist_ok=True)
    kind = "move" if args.move else "timeline" if args.timeline else "fixed"
    log_path = log_dir / f"{args.world}_{kind}_{datetime.now():%Y%m%d_%H%M%S}.csv"

    m = mavutil.mavlink_connection("udpin:0.0.0.0:14540")
    print("Waiting for PX4...")
    m.wait_heartbeat()
    print(f"Connected to PX4! Saving to {log_path.name}")

    stage_i = 0
    name, east, north, duration = stages[0]
    if changes_wind:
        set_wind(args.world, east, north)
    wind_ms, wind_from_deg = to_speed_dir(east, north)
    print(f"--- stage '{name}': wind {wind_ms:.2f} m/s from {wind_from_deg:.0f} deg")

    heading = height = roll = lat = lon = None
    base_lat = base_lon = path_heading = None   # the planned line, fixed when the test starts
    last_sent = 0.0                             # last offset sent to PX4
    last = 0.0
    start = time.monotonic()
    stage_start = None          # the test starts when the drone first reaches spraying height
    rows = 0

    with open(log_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(COLUMNS)
        try:
            while True:
                msg = m.recv_match(type=["GLOBAL_POSITION_INT", "ATTITUDE"], blocking=True, timeout=5)
                if msg is None:
                    print("no data from PX4...")
                    continue
                if msg.get_type() == "GLOBAL_POSITION_INT":
                    if msg.hdg != 65535:
                        heading = msg.hdg / 100
                    height = msg.relative_alt / 1000
                    lat, lon = msg.lat / 1e7, msg.lon / 1e7
                else:
                    roll = math.degrees(msg.roll)

                now = time.monotonic()
                if None in (heading, height, roll, lat) or now - last < 1:
                    continue
                last = now

                if height < MIN_HEIGHT_M:
                    print(f"height {height:4.2f} m - waiting for spraying height")
                    continue

                if stage_start is None:
                    stage_start = now
                    base_lat, base_lon, path_heading = lat, lon, heading
                    if changes_wind:
                        print("Spraying height reached - test starts")

                # time for the next stage?
                if duration is not None and now - stage_start >= duration:
                    if stage_i < len(stages) - 1:
                        stage_i += 1
                        name, east, north, duration = stages[stage_i]
                        set_wind(args.world, east, north)
                        wind_ms, wind_from_deg = to_speed_dir(east, north)
                        stage_start = now
                        print(f"--- stage '{name}': wind {wind_ms:.2f} m/s from {wind_from_deg:.0f} deg")
                    else:
                        if args.move:
                            send_reposition(m, base_lat, base_lon)     # back to the planned line
                        print(f"=== Finished - saved {rows} rows to {log_path.name}. "
                              "You can land now (commander land) ===")
                        break

                # with --move the drone may move, so C2 uses the planned line's direction
                c2_heading = path_heading if args.move else heading
                r = recommend(wind_ms=wind_ms, wind_dir_deg=wind_from_deg, heading_deg=c2_heading,
                              temp_c=TEMP_C, rh_pct=RH_PCT, height_m=height)

                if r["mode"] == "CORRECT":
                    tilt = r["nozzle_tilt_deg"] if r["nozzle_tilt_side"] == "right" else -r["nozzle_tilt_deg"]
                else:
                    tilt = 0.0
                servo = tilt - roll    # the nozzle is fixed to the body: remove the drone's own lean

                # path offset as one signed number: + = move right, - = move left
                offset_cmd = r["path_offset_m"] or 0.0
                if r["path_offset_side"] == "left":
                    offset_cmd = -offset_cmd
                if r["mode"] != "CORRECT":
                    offset_cmd = 0.0   # no correction -> stay on the planned line

                if args.move and abs(offset_cmd - last_sent) > RESEND_M:
                    target_lat, target_lon = offset_point(base_lat, base_lon, path_heading, offset_cmd)
                    send_reposition(m, target_lat, target_lon)
                    last_sent = offset_cmd
                    print(f">>> sent to PX4: move to {offset_cmd:+.2f} m from the planned line")

                side = side_position(lat, lon, base_lat, base_lon, path_heading)

                drift = "-" if r["drift_m"] is None else f"{r['drift_m']:.1f}"
                print(f"{name:9s} | {r['mode']:13s} | wind {wind_ms:4.2f} | cw {r['crosswind_ms']:4.2f} "
                      f"{r['wind_from_side']:5s} | drift {drift:>5s} | tilt {tilt:+5.1f} | roll {roll:+4.1f} "
                      f"| servo {servo:+5.1f} | offset {offset_cmd:+.2f} | side pos {side:+.2f}")

                writer.writerow([round(now - start, 1), name, round(heading, 1), round(height, 2),
                                 round(roll, 2), round(wind_ms, 2), round(wind_from_deg, 1), r["mode"],
                                 r["crosswind_ms"], r["wind_from_side"], r["drift_m"], r["drift_risk"],
                                 round(tilt, 1), round(servo, 1), r["path_offset_m"], r["path_offset_side"],
                                 round(offset_cmd, 2), round(side, 2)])
                f.flush()
                rows += 1
        except KeyboardInterrupt:
            print(f"\nStopped. Saved {rows} rows to {log_path}")


if __name__ == "__main__":
    main()
