"""Scenario table for the recommendation logic (test level 2).

Run from the repo root:
    python -m component2_wind_spraying.drift_model.demo_recommend
"""
import pandas as pd

from .recommend import recommend

# name, wind (m/s at 2 m), wind from (deg), flight heading (deg), temp, RH, height, droplet class
SCENARIOS = [
    ("Calm morning",                 0.4,  90, 0, 24, 85, 2.5, "F-M"),
    ("Light wind from right",        1.5,  90, 0, 28, 70, 2.5, "F-M"),
    ("Moderate wind from right",     3.0,  90, 0, 30, 60, 2.5, "F-M"),
    ("Moderate wind from left",      3.0, 270, 0, 30, 60, 2.5, "F-M"),
    ("Wind along flight line",       3.0,   0, 0, 30, 60, 2.5, "F-M"),
    ("Wind at 45 deg",               3.0,  45, 0, 30, 60, 2.5, "F-M"),
    ("Moderate wind, flying high",   3.0,  90, 0, 30, 60, 3.4, "F-M"),
    ("Moderate wind, very fine",     3.0,  90, 0, 32, 45, 2.5, "VF-F"),
    ("Moderate wind, coarse",        3.0,  90, 0, 30, 60, 2.5, "C-VC"),
    ("Windy, hot and dry",           4.3,  90, 0, 34, 40, 2.5, "F-M"),
    ("Strong wind",                  5.5,  90, 0, 30, 60, 2.5, "F-M"),
]

rows = []
for name, wind, wdir, head, temp, rh, h, drop in SCENARIOS:
    r = recommend(wind, wdir, head, temp, rh, height_m=h, droplet_class=drop)
    rows.append({
        "scenario": name, "wind": wind, "droplet": drop, "height": h,
        "mode": r["mode"], "drift_m": r["drift_m"], "risk": r["drift_risk"],
        "shift_m": r["spray_shift_m"],
        "nozzle": f'{r["nozzle_tilt_deg"]} {r["nozzle_tilt_side"] or ""}'.strip(),
        "path": f'{r["path_offset_m"]} {r["path_offset_side"] or ""}'.strip(),
        "droplet_advice": r["droplet_advice"], "height_advice": r["height_advice"],
    })

table = pd.DataFrame(rows)
pd.set_option("display.width", 200)
print(table.to_string(index=False))
table.to_csv("component2_wind_spraying/evaluation/recommendation_scenarios.csv", index=False)
print("\nsaved: component2_wind_spraying/evaluation/recommendation_scenarios.csv")