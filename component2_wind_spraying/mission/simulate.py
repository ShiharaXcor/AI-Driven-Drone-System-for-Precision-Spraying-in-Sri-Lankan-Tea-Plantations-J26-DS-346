"""Component 2 - mission simulation (wind-adaptive spraying over a whole field).

What it does, step by step:
1. Plans the spray lines over a rectangular field (back-and-forth "lawnmower" pattern).
   The heading flips on every line, so the same wind is on the right, then on the left.
2. Moves a simulated drone along the lines, one time step (dt seconds) at a time.
3. At every step it takes the wind for that moment (steady, gusty or calm scenario)
   and asks recommend() what to do.
4. CORRECT / NO_CORRECTION -> the drone sprays; the flight line is shifted by the path
   offset and the nozzle is tilted.  STRONG_WIND -> the drone HOLDS (hovers, no spray)
   until the wind drops again.
   The decision uses the wind measured one step earlier (sensor/update delay), while the
   spray lands with the wind of this moment - so gusts leave a small, realistic error.
5. Records where the spray would land WITHOUT correction and WITH correction, a log of
   decisions, and a summary for the whole mission.

This is a simulation of the decision system, not of the spray physics: the landing points
use the same simple shift model as recommend.py.  The planned/corrected waypoints are the
part that can later be sent to a flight simulator (ArduPilot SITL) or a real autopilot.
"""
import math
import random
from functools import lru_cache

from ..drift_model import recommend as rec

M_PER_DEG_LAT = 111_320.0
TURN_S = 4.0                       # assumption: time to turn onto the next line (s)


# ---------------- geometry helpers (metres <-> lat/lon) ----------------
def to_latlon(lat0, lon0, east_m, north_m):
    lat = lat0 + north_m / M_PER_DEG_LAT
    lon = lon0 + east_m / (M_PER_DEG_LAT * math.cos(math.radians(lat0)))
    return round(lat, 7), round(lon, 7)


def forward(bearing_deg):
    """Unit vector (east, north) pointing along a bearing (0 = north, 90 = east)."""
    b = math.radians(bearing_deg)
    return math.sin(b), math.cos(b)


def right_of(bearing_deg):
    """Unit vector (east, north) pointing to the RIGHT of a drone flying on this bearing."""
    b = math.radians(bearing_deg)
    return math.cos(b), -math.sin(b)


# ---------------- 1. plan the spray lines ----------------
def plan_lines(length_m, width_m, swath_m, row_bearing_deg):
    """Back-and-forth spray lines in local metres (east, north), centred on the field centre."""
    n = max(1, math.ceil(width_m / swath_m))
    fx, fy = forward(row_bearing_deg)
    rx, ry = right_of(row_bearing_deg)
    lines = []
    for i in range(n):
        c = -width_m / 2 + swath_m / 2 + i * swath_m          # sideways position of line i
        a = (c * rx - length_m / 2 * fx, c * ry - length_m / 2 * fy)
        b = (c * rx + length_m / 2 * fx, c * ry + length_m / 2 * fy)
        if i % 2 == 0:
            heading, start, end = row_bearing_deg % 360, a, b
        else:
            heading, start, end = (row_bearing_deg + 180) % 360, b, a
        lines.append({"index": i, "heading_deg": round(heading, 1), "start": start, "end": end})
    return lines


# ---------------- 2. wind scenarios ----------------
def wind_at(scenario, frac, base_speed, base_dir, rng):
    """Wind (speed at 2 m, direction FROM) at a fraction 0..1 of the planned mission time."""
    if scenario == "calm":
        speed = 0.4 + 0.3 * rng.random()
    elif scenario == "steady":
        speed = base_speed + rng.gauss(0, 0.2)
    else:   # "gusty": wind slowly rises, one gust above the strong-wind limit, then eases
        speed = base_speed * (0.8 + 0.6 * frac) + rng.gauss(0, 0.25)
        if 0.45 <= frac <= 0.55:
            speed = max(speed, rec.STRONG_WIND_MS + 0.6 + rng.random() * 0.4)
        elif frac > 0.55:
            speed = base_speed + rng.gauss(0, 0.25)
    direction = base_dir + 15 * math.sin(2 * math.pi * 1.5 * frac) + rng.gauss(0, 4)
    return max(0.0, round(speed, 1)), round(direction) % 360


@lru_cache(maxsize=20000)
def _cached_recommend(wind, wdir, heading, temp, rh, height, swath, droplet, max_drift):
    return rec.recommend(wind, wdir, heading, temp, rh, height_m=height, swath_m=swath,
                         droplet_class=droplet, max_drift_m=max_drift)


def _num(v):
    return v.item() if hasattr(v, "item") else v


# ---------------- 3. run the mission ----------------
def simulate(center_lat=6.955, center_lon=80.775, length_m=100.0, width_m=60.0, row_bearing_deg=0.0,
             swath_m=5.5, height_m=2.5, droplet_class="F-M", speed_ms=4.0, temp_c=28.0, rh_pct=70.0,
             wind_ms=2.5, wind_dir_deg=90.0, scenario="gusty", max_drift_m=20.0, dt=1.0, seed=42,
             max_steps=4000):
    lines = plan_lines(length_m, width_m, swath_m, row_bearing_deg)
    planned_time = len(lines) * (length_m / speed_ms + TURN_S)
    rng = random.Random(seed)

    steps, events = [], []
    t, li, along = 0.0, 0, 0.0
    prev_status, prev_side = None, None
    hold_s = 0.0
    last_warn_t = -1e9
    prev_wind = None

    def log(kind, text):
        events.append({"t": round(t, 1), "kind": kind, "text": text})

    log("info", f"Mission planned: {len(lines)} lines of {length_m:.0f} m, swath {swath_m} m")

    while li < len(lines) and len(steps) < max_steps:
        line = lines[li]
        h = line["heading_deg"]
        if along == 0.0 and prev_status != "HOLD":
            log("line", f"Line {li + 1}/{len(lines)} started, heading {h:.0f}°")

        frac = min(t / planned_time, 1.0)
        w, wd = wind_at(scenario, frac, wind_ms, wind_dir_deg, rng)          # wind right now
        dw, dwd = prev_wind if prev_wind else (w, wd)                        # wind the decision is based on
        prev_wind = (w, wd)                                                  # (1 step sensor/update delay)
        r = dict(_cached_recommend(dw, dwd, round(h) % 360, temp_c, rh_pct, height_m, swath_m,
                                   droplet_class, max_drift_m))
        r = {k: _num(v) for k, v in r.items()}

        fx, fy = forward(h)
        rx, ry = right_of(h)
        px, py = line["start"][0] + fx * along, line["start"][1] + fy * along      # planned point
        status = "HOLD" if r["mode"] == "STRONG_WIND" else "SPRAYING"

        # where the spray really lands uses the wind RIGHT NOW (it may have changed since the decision)
        cw_now = rec.signed_crosswind(w, wd, h)                               # + = from the right
        land_unc = -math.copysign(rec.spray_shift_m(cw_now, height_m, droplet_class), cw_now)
        sign = 1 if r["wind_from_side"] == "right" else -1
        if r["mode"] == "CORRECT":
            nozzle_part = height_m * math.tan(math.radians(r["nozzle_tilt_deg"]))
            path_lat = sign * r["path_offset_m"]
            land_corr = sign * (r["path_offset_m"] + nozzle_part) + land_unc
        else:
            path_lat, land_corr = 0.0, land_unc

        drone = (px + rx * path_lat, py + ry * path_lat)
        step = {
            "t": round(t, 1), "line": li + 1, "heading_deg": h, "status": status,
            "wind_ms": w, "wind_dir_deg": wd, "decision_wind_ms": dw, "mode": r["mode"],
            "crosswind_ms": r["crosswind_ms"], "wind_from_side": r["wind_from_side"],
            "drift_m": r["drift_m"], "drift_risk": r["drift_risk"],
            "nozzle_tilt_deg": r["nozzle_tilt_deg"], "nozzle_tilt_side": r["nozzle_tilt_side"],
            "path_offset_m": r["path_offset_m"], "path_offset_side": r["path_offset_side"],
            "droplet_advice": r["droplet_advice"], "height_advice": r["height_advice"],
            "drone": to_latlon(center_lat, center_lon, *drone),
            "planned": to_latlon(center_lat, center_lon, px, py),
        }
        if status == "SPRAYING":
            step["miss_uncorrected_m"] = round(abs(land_unc), 2)
            step["miss_corrected_m"] = round(abs(land_corr), 2)
            step["land_uncorrected"] = to_latlon(center_lat, center_lon, px + rx * land_unc, py + ry * land_unc)
            step["land_corrected"] = to_latlon(center_lat, center_lon, px + rx * land_corr, py + ry * land_corr)
        steps.append(step)

        # ---- decision log: only log changes ----
        if status != prev_status:
            if status == "HOLD":
                log("critical", f"Wind {w} m/s above {rec.STRONG_WIND_MS} m/s → HOLD, spraying paused")
            elif prev_status == "HOLD":
                log("good", f"Wind down to {w} m/s → resume spraying")
        if status == "SPRAYING" and r["mode"] == "CORRECT" and r["nozzle_tilt_side"] != prev_side:
            log("info", f"Wind from the {r['nozzle_tilt_side']} ({r['crosswind_ms']} m/s crosswind) → "
                        f"tilt {r['nozzle_tilt_deg']}° {r['nozzle_tilt_side']}, path {r['path_offset_m']} m {r['nozzle_tilt_side']}")
            prev_side = r["nozzle_tilt_side"]
        if status == "SPRAYING" and r["drift_risk"] == "HIGH" and t - last_warn_t >= 60:
            last_warn_t = t
            advice = f" → switch to {r['droplet_advice']}" if r["droplet_advice"] else " → no safe droplet class"
            log("warning", f"Predicted drift {r['drift_m']} m above {max_drift_m} m{advice}")
        prev_status = status

        # ---- move on ----
        t += dt
        if status == "HOLD":
            hold_s += dt
            continue
        along += speed_ms * dt
        line_length = length_m
        if along >= line_length:
            li += 1
            along = 0.0
            prev_side = None
            t += TURN_S

    spraying = [s for s in steps if s["status"] == "SPRAYING"]
    corrected = [s for s in spraying if s["mode"] == "CORRECT"]
    mean = lambda xs: round(sum(xs) / len(xs), 2) if xs else 0.0
    summary = {
        "lines": len(lines),
        "lines_completed": li,
        "duration_s": round(t, 1),
        "hold_s": round(hold_s, 1),
        "spray_steps": len(spraying),
        "corrected_share_pct": round(100 * len(corrected) / len(spraying), 1) if spraying else 0.0,
        "mean_miss_uncorrected_m": mean([s["miss_uncorrected_m"] for s in spraying]),
        "mean_miss_corrected_m": mean([s["miss_corrected_m"] for s in spraying]),
        "high_drift_share_pct": round(100 * sum(s["drift_risk"] == "HIGH" for s in spraying) / len(spraying), 1) if spraying else 0.0,
    }
    log("info", f"Mission finished in {summary['duration_s']:.0f} s ({summary['hold_s']:.0f} s on hold)")

    corners = [(-width_m / 2, -length_m / 2), (width_m / 2, -length_m / 2), (width_m / 2, length_m / 2), (-width_m / 2, length_m / 2)]
    rx0, ry0 = right_of(row_bearing_deg)
    fx0, fy0 = forward(row_bearing_deg)
    field = [to_latlon(center_lat, center_lon, c * rx0 + a * fx0, c * ry0 + a * fy0) for c, a in corners]
    planned_lines = [{"index": l["index"] + 1, "heading_deg": l["heading_deg"],
                      "start": to_latlon(center_lat, center_lon, *l["start"]),
                      "end": to_latlon(center_lat, center_lon, *l["end"])} for l in lines]
    return {"field": field, "lines": planned_lines, "steps": steps, "events": events, "summary": summary,
            "strong_wind_ms": rec.STRONG_WIND_MS, "max_drift_m": max_drift_m}
