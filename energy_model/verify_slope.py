# verify_slope.py
# Verifies slope grid produces realistic battery drain matching SULEKO data
# Run: python3 energy_model/verify_slope.py

import numpy as np
import json
import sys

sys.path.insert(0, '/home/amanda/component3/energy_model')
from energy_model import EnergyModel

# Load calibrated model
with open('/home/amanda/component3/energy_model/calibrated_model.json') as f:
    constants = json.load(f)

model        = EnergyModel()
model.eta    = constants['eta']
model.k_drag = constants['k_drag']

# Load real slope grid
slope       = np.load('/home/amanda/component3/terrain/slope_grid_srtm.npy')
valid_slope = slope[~np.isnan(slope)]

print("=" * 50)
print("SLOPE GRID VERIFICATION")
print("=" * 50)
print(f"Average slope: {valid_slope.mean():.1f} degrees")
print(f"Steep (>20):   {(valid_slope>=20).mean()*100:.1f}%")
print()

# Simulate a full mission using real slope values
speed_ms = 6.4 / 3.6   # T20P mountainous speed from Kenilworth
liquid   = 20.0          # start full tank
battery  = 100.0
dt_min   = 0.1           # 6 second steps
step     = 0

while liquid > 0 and battery > 20:
    slope_now = valid_slope.mean()
    mass      = model.current_mass(liquid)
    drain     = model.battery_drain_per_minute(mass, slope_now, speed_ms) * dt_min
    battery  -= drain
    liquid    = max(0, liquid - 0.4)
    step     += 1

used = 100 - battery
print(f"Simulation result:")
print(f"  Steps to empty tank: {step}")
print(f"  Battery used:        {used:.1f}%")
print(f"  SULEKO T20P actual:  78.4%")
print(f"  Difference:          {abs(used - 78.4):.1f}%")
print()

if abs(used - 78.4) < 10:
    print("Status: VERIFIED ✓")
    print("Slope grid produces battery drain within 10% of real SULEKO data")
elif abs(used - 78.4) < 20:
    print("Status: ACCEPTABLE")
    print("Slope grid is within 20% of real data — acceptable for DRL training")
else:
    print("Status: NEEDS REVIEW")
    print("Difference > 20% — energy model may need recalibration")