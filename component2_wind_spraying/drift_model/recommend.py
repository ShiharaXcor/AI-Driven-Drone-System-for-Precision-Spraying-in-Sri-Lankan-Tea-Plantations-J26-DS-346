"""Component 2 - wind-adaptive spray recommendation (standalone).

What it does, step by step:
1. Works out the crosswind (the part of the wind blowing across the flight line)
   and which side it comes from (left or right of the drone).
2. Predicts the drift distance with the trained ML model (predict_drift).
3. Estimates how far the crosswind pushes the spray sideways while it falls
   (simple physics: shift = crosswind x fall time).
4. Corrects that shift: first by tilting the nozzle into the wind, then (if the
   tilt is not enough) by moving the flight path towards the wind.
5. In strong wind it gives NO correction and only flags that another decision
   is needed (to be connected to the other components later).

The values marked "assumption" must be agreed with the team / calibrated in a field trial.
"""
import math

from .features import VALID_RANGES
from .predict import predict_drift

# ---------------- settings (assumptions, easy to change) ----------------
STRONG_WIND_MS = 4.5            # assumption: 2 m wind above this -> no correction
MIN_CROSSWIND_MS = 0.5          # below this the spray is hardly pushed -> no correction
MAX_NOZZLE_TILT_DEG = 30.0      # assumption: test platforms tilt +/-30 deg (Chen P. et al., 2022); set to real drone value
DOWNWASH_MS = 2.0               # assumption: rotor downwash strongly reduces drift (Liu et al., 2021)
SETTLING_SPEED_MS = {"VF-F": 0.3, "F-M": 0.7, "M-C": 1.2, "C-VC": 1.8}   # assumption: approx. droplet fall speed
MAX_RECOMMENDED_HEIGHT_M = 2.5  # fly at <= 2.5 m to reduce drift (Chen P. et al., 2022)
DROPLETS_FINE_TO_COARSE = ["VF-F", "F-M", "M-C", "C-VC"]
CW_MIN, CW_MAX = VALID_RANGES["crosswind_ms"]


def signed_crosswind(wind_ms, wind_dir_deg, heading_deg):
    """Crosswind in m/s. Positive = wind comes FROM the drone's right side.

    wind_dir_deg: direction the wind comes FROM (0 = north, 90 = east).
    heading_deg:  direction the drone flies TO (0 = north, 90 = east).
    """
    return wind_ms * math.sin(math.radians(wind_dir_deg - heading_deg))


def spray_shift_m(crosswind_ms, height_m, droplet_class):
    """How far (m) the crosswind pushes the spray sideways while it falls."""
    fall_time_s = height_m / (SETTLING_SPEED_MS[droplet_class] + DOWNWASH_MS)
    return abs(crosswind_ms) * fall_time_s


def recommend(wind_ms, wind_dir_deg, heading_deg, temp_c, rh_pct,
              height_m=2.5, swath_m=5.5, droplet_class="F-M", max_drift_m=20.0):
    """Return the drift prediction and the recommended correction as a dictionary.

    wind_ms is the wind speed at 2 m height (m/s).
    mode is one of: "CORRECT", "NO_CORRECTION", "STRONG_WIND".
    """
    if droplet_class not in DROPLETS_FINE_TO_COARSE:
        raise ValueError(f"Unknown droplet_class '{droplet_class}'. Use one of {DROPLETS_FINE_TO_COARSE}.")

    cw = signed_crosswind(wind_ms, wind_dir_deg, heading_deg)
    side = "right" if cw > 0 else "left"   # side the wind comes FROM = side we correct towards

    result = {
        "mode": None,
        "drift_m": None,              # ML prediction (m)
        "drift_risk": None,           # "OK" or "HIGH" compared with max_drift_m
        "crosswind_ms": round(abs(cw), 2),
        "wind_from_side": side,
        "spray_shift_m": 0.0,         # how far the spray lands off target (m)
        "nozzle_tilt_deg": 0.0,
        "nozzle_tilt_side": None,
        "path_offset_m": 0.0,
        "path_offset_side": None,
        "offset_capped": False,
        "droplet_advice": None,
        "height_advice": None,
        "needs_external_decision": False,   # for later integration with the other components
        "reason": "",
    }

    # 1. Strong wind -> no correction at all, only flag it
    if wind_ms > STRONG_WIND_MS:
        result["mode"] = "STRONG_WIND"
        result["needs_external_decision"] = True
        result["reason"] = (f"Strong wind ({wind_ms:.1f} m/s > {STRONG_WIND_MS} m/s): "
                            "no correction given.")
        return result

    # 2. ML drift prediction (crosswind kept inside the range the model learned)
    cw_model = min(max(abs(cw), CW_MIN), CW_MAX)
    drift = predict_drift(cw_model, height_m, swath_m, temp_c, rh_pct, droplet_class)
    result["drift_m"] = round(drift, 1)
    result["drift_risk"] = "HIGH" if drift > max_drift_m else "OK"

    # If drift is too high, suggest the finest coarser droplet class that is safe
    if drift > max_drift_m:
        coarser = DROPLETS_FINE_TO_COARSE[DROPLETS_FINE_TO_COARSE.index(droplet_class) + 1:]
        for d in coarser:
            if predict_drift(cw_model, height_m, swath_m, temp_c, rh_pct, d) <= max_drift_m:
                result["droplet_advice"] = d
                break

    # Advice from literature (only when there is a real crosswind)
    if abs(cw) >= MIN_CROSSWIND_MS:
        if height_m > MAX_RECOMMENDED_HEIGHT_M:
            result["height_advice"] = MAX_RECOMMENDED_HEIGHT_M
        if droplet_class == "VF-F" and result["droplet_advice"] is None:
            result["droplet_advice"] = "F-M"   # avoid very fine droplets (Chen S. et al., 2020)

    # 3. Very light crosswind -> nothing to correct
    if abs(cw) < MIN_CROSSWIND_MS:
        result["mode"] = "NO_CORRECTION"
        result["reason"] = "Crosswind is very light, no correction needed."
        return result

    # 4. Correction: nozzle tilt first, path offset for the rest
    shift = spray_shift_m(cw, height_m, droplet_class)
    max_nozzle_shift = height_m * math.tan(math.radians(MAX_NOZZLE_TILT_DEG))
    nozzle_part = min(shift, max_nozzle_shift)
    tilt = math.degrees(math.atan(nozzle_part / height_m))
    path_part = shift - nozzle_part
    capped = path_part > swath_m / 2
    if capped:
        path_part = swath_m / 2

    result.update(
        mode="CORRECT",
        spray_shift_m=round(shift, 2),
        nozzle_tilt_deg=round(tilt, 1),
        nozzle_tilt_side=side,
        path_offset_m=round(path_part, 2),
        path_offset_side=side if path_part > 0 else None,
        offset_capped=capped,
        reason=(f"Wind from the {side} pushes the spray {shift:.2f} m. "
                f"Tilt nozzle {tilt:.1f} deg to the {side}"
                + (f" and move the path {path_part:.2f} m to the {side}." if path_part > 0 else ".")),
    )
    return result