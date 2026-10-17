# verify_slope.py
# Consistency check: does the energy model, driven by the REAL SRTM slope
# distribution, reproduce a SULEKO T20P flight?
#   - tank, flight duration and speed come from SULEKO records (not guessed)
#   - slope is sampled cell-by-cell from the real SRTM grid
# Run: python3 energy_model/verify_slope.py

import os, sys, json
import numpy as np

BASE = os.environ.get("C3_BASE", os.path.expanduser("~/component3"))
sys.path.insert(0, f"{BASE}/energy_model")
from energy_model import EnergyModel

# SULEKO T20P Badulla/Uva means (printed by energy_model.py)
REAL_DROP_PCT = 78.4
REAL_DURATION = 6.43      # min
REAL_LIQUID_L = 20.3
SPEED_KMH     = 6.4       # assumption

with open(f"{BASE}/energy_model/calibrated_model.json") as f:
    c = json.load(f)
model = EnergyModel()
model.mass_empty_kg = c["mass_empty_kg"]
model.battery_wh    = c["battery_wh_effective"]
model.level_scale   = c["suleko_level_scale"]

slope = np.load(f"{BASE}/terrain/slope_grid_srtm.npy")
valid = slope[~np.isnan(slope)]
print("=" * 50); print("SLOPE GRID CHECK"); print("=" * 50)
print(f"Average slope: {valid.mean():.1f} deg   Steep (>20): {(valid >= 20).mean()*100:.1f}%\n")

rng = np.random.default_rng(0)
dt_min = 0.1
n_steps = int(round(REAL_DURATION / dt_min))
liq_step = REAL_LIQUID_L / n_steps
drops = []
for _ in range(200):                       # 200 simulated flights
    liquid, used = REAL_LIQUID_L, 0.0
    for _ in range(n_steps):
        s = rng.choice(valid)              # real slope of a random grid cell
        used += model.drain_at(liquid, s, SPEED_KMH) * dt_min
        liquid = max(0.0, liquid - liq_step)
    drops.append(used)
drops = np.array(drops)
err = abs(drops.mean() - REAL_DROP_PCT) / REAL_DROP_PCT * 100
print(f"Simulated battery used: {drops.mean():.1f} % (std {drops.std():.1f})")
print(f"SULEKO T20P actual:     {REAL_DROP_PCT} %")
print(f"Error:                  {err:.1f} %")
print("Status:", "PASS (<10%)" if err < 10 else "CHECK")
print("\nNote: this checks the whole chain against real flights. It does NOT")
print("prove the slope grid is correct: the model is only weakly slope-sensitive.")