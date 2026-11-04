"""Component 2 - live loop for the PX4 + Gazebo simulator.

Every second it:
  1. reads the drone's heading, height and roll from PX4 (MAVLink, port 14540),
  2. knows the wind (fixed from the world file, or changed step by step with --timeline),
  3. runs recommend() - the same C2 code as the backend,
  4. prints the result and saves it to a CSV file in simulation/c2/logs/.

Run (WSL Ubuntu, simulator already running, venv active):
    cd simulation
    python3 c2_live.py --world c2_windy              # fixed wind from the world file
    python3 c2_live.py --world c2_windy --timeline   # calm -> moderate -> strong -> moderate
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

# Timeline for --timeline: (stage name, wind toward EAST m/s, wind toward NORTH m/s, seconds)
TIMELINE = [
    ("calm",     0.3, 0.0, 60),
    ("moderate", 2.0, 1.0, 60),
    ("strong",   5.0, 2.0, 60),
    ("moderate", 2.0, 1.0, 60),
]

COLUMNS = ["t_s", "stage", "heading_deg", "height_m", "roll_deg", "wind_ms", "wind_from_deg",
           "mode", "crosswind_ms", "wind_from_side", "drift_m", "drift_risk",
           "tilt_deg", "servo_deg", "path_offset_m", "path_offset_side"]


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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--world", default="c2_windy",
                        help="the world the simulator is running: c2_calm, c2_windy or c2_strong")
    parser.add_argument("--timeline", action="store_true",
                        help="change the wind step by step: calm -> moderate -> strong -> moderate")
    args = parser.parse_args()

    if args.timeline:
        stages = TIMELINE
    else:
        east, north = world_wind(args.world)
        stages = [("fixed", east, north, None)]          # None = no time limit

    log_dir = HERE / "logs"
    log_dir.mkdir(exist_ok=True)
    kind = "timeline" if args.timeline else "fixed"
    log_path = log_dir / f"{args.world}_{kind}_{datetime.now():%Y%m%d_%H%M%S}.csv"

    m = mavutil.mavlink_connection("udpin:0.0.0.0:14540")
    print("Waiting for PX4...")
    m.wait_heartbeat()
    print(f"Connected to PX4! Saving to {log_path.name}")

    stage_i = 0
    name, east, north, duration = stages[0]
    if args.timeline:
        set_wind(args.world, east, north)
    wind_ms, wind_from_deg = to_speed_dir(east, north)
    print(f"--- stage '{name}': wind {wind_ms:.2f} m/s from {wind_from_deg:.0f} deg")

    heading = height = roll = None
    last = 0.0
    start = time.monotonic()
    stage_start = None          # the timeline starts when the drone first reaches spraying height
    finished = False
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
                else:
                    roll = math.degrees(msg.roll)

                now = time.monotonic()
                if None in (heading, height, roll) or now - last < 1:
                    continue
                last = now

                if height < MIN_HEIGHT_M:
                    print(f"height {height:4.2f} m - waiting for spraying height")
                    continue

                if stage_start is None:
                    stage_start = now
                    if args.timeline:
                        print("Spraying height reached - timeline starts")

                # time for the next stage?
                if duration is not None and now - stage_start >= duration:
                    if stage_i < len(stages) - 1:
                        stage_i += 1
                        name, east, north, duration = stages[stage_i]
                        set_wind(args.world, east, north)
                        wind_ms, wind_from_deg = to_speed_dir(east, north)
                        stage_start = now
                        print(f"--- stage '{name}': wind {wind_ms:.2f} m/s from {wind_from_deg:.0f} deg")
                    elif not finished:
                        print(f"=== Timeline finished - saved {rows} rows to {log_path.name}. "
                              "You can land now (commander land) ===")
                        break

                r = recommend(wind_ms=wind_ms, wind_dir_deg=wind_from_deg, heading_deg=heading,
                              temp_c=TEMP_C, rh_pct=RH_PCT, height_m=height)

                if r["mode"] == "CORRECT":
                    tilt = r["nozzle_tilt_deg"] if r["nozzle_tilt_side"] == "right" else -r["nozzle_tilt_deg"]
                else:
                    tilt = 0.0
                servo = tilt - roll    # the nozzle is fixed to the body: remove the drone's own lean

                drift = "-" if r["drift_m"] is None else f"{r['drift_m']:.1f}"
                print(f"{name:8s} | {r['mode']:13s} | wind {wind_ms:4.2f} | cw {r['crosswind_ms']:4.2f} "
                      f"{r['wind_from_side']:5s} | drift {drift:>5s} | tilt {tilt:+5.1f} | roll {roll:+4.1f} "
                      f"| servo {servo:+5.1f} | offset {r['path_offset_m']:.2f}")

                writer.writerow([round(now - start, 1), name, round(heading, 1), round(height, 2),
                                 round(roll, 2), round(wind_ms, 2), round(wind_from_deg, 1), r["mode"],
                                 r["crosswind_ms"], r["wind_from_side"], r["drift_m"], r["drift_risk"],
                                 round(tilt, 1), round(servo, 1), r["path_offset_m"], r["path_offset_side"]])
                f.flush()
                rows += 1
        except KeyboardInterrupt:
            print(f"\nStopped. Saved {rows} rows to {log_path}")


if __name__ == "__main__":
    main()