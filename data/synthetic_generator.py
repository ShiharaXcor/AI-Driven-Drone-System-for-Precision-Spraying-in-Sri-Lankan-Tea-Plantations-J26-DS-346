# synthetic_generator.py
# Component 3 - Synthetic flight telemetry from the calibrated energy model
#
# Every row is SYNTHETIC but anchored to real data:
#   - slopes   : sampled from the real SRTM slope grid of Ouvahkelle Estate
#   - physics  : calibrated energy model (fitted on Kenilworth telemetry)
#   - flights  : liquid load, duration and speed drawn from SULEKO statistics
#   - noise    : 9 % multiplicative noise = measured model error on SULEKO T20P
#
# Run:  cd ~/component3 && source venv/bin/activate
#       python3 data/synthetic_generator.py

import os, sys, json, glob
import numpy as np
import pandas as pd

BASE = os.environ.get("C3_BASE", os.path.expanduser("~/component3"))
sys.path.insert(0, f"{BASE}/energy_model")
from energy_model import EnergyModel

SEED        = 42
N_FLIGHTS   = 250          # SULEKO has 163 mountain flights; 250 gives variety
DT_S        = 2.0          # seconds between rows
NOISE_SD    = 0.09         # lognormal sigma = model error on SULEKO T20P
RTH_BATTERY = 20.0         # return-to-home threshold (%)


def load_model():
    m = EnergyModel()
    with open(f"{BASE}/energy_model/calibrated_model.json") as f:
        c = json.load(f)
    m.mass_empty_kg = c["mass_empty_kg"]
    m.battery_wh    = c["battery_wh_effective"]
    m.level_scale   = c["suleko_level_scale"]
    return m, c


def find_slope_grid():
    hits = glob.glob(f"{BASE}/**/slope_grid_srtm.npy", recursive=True)
    if not hits:
        raise FileNotFoundError("slope_grid_srtm.npy not found - run terrain_processor.py first")
    return np.load(hits[0]), hits[0]


def simulate_flight(model, grid, rng, fid):
    rows_, cols_ = grid.shape
    r, c   = rng.integers(0, rows_), rng.integers(0, cols_)
    liquid = rng.uniform(18.5, 20.5)
    flow   = liquid / rng.uniform(5.5, 7.0) / 60.0       # L/s, empties in ~6 min
    speed  = rng.normal(6.4, 0.8)                        # km/h, per-flight cruise
    battery, t, rows = 100.0, 0.0, []
    while liquid > 0.3 and battery > RTH_BATTERY:
        slope = float(grid[r, c])
        v_ms  = max(1.0, speed + rng.normal(0, 0.4)) / 3.6
        cost  = model.energy_cost(liquid, slope, v_ms, dt=DT_S)
        cost *= rng.lognormal(0, NOISE_SD)
        rows.append(dict(flight_id=fid, time_s=round(t, 1), row=r, col=c,
                         slope_deg=round(slope, 2), speed_ms=round(v_ms, 3),
                         liquid_L=round(liquid, 3),
                         mass_kg=round(model.current_mass(liquid), 2),
                         battery_pct=round(battery, 3),
                         step_cost_pct=round(cost, 5),
                         drain_pct_min=round(cost / DT_S * 60, 3)))
        battery -= cost
        liquid  -= flow * DT_S
        t       += DT_S
        # move to a neighbouring cell about every 10 s (random walk on the grid)
        if int(t) % 10 == 0:
            r = int(np.clip(r + rng.integers(-1, 2), 0, rows_ - 1))
            c = int(np.clip(c + rng.integers(-1, 2), 0, cols_ - 1))
    return rows


def main():
    rng = np.random.default_rng(SEED)
    model, const = load_model()
    grid, path = find_slope_grid()
    print(f"Slope grid: {path}  shape={grid.shape}  mean={grid.mean():.1f} deg")

    rows = []
    for fid in range(N_FLIGHTS):
        rows += simulate_flight(model, grid, rng, fid)
    df = pd.DataFrame(rows)
    df["source"] = "synthetic: calibrated energy model + SRTM slopes"
    out = f"{BASE}/data/synthetic_flights.csv"
    df.to_csv(out, index=False)

    # ---- accuracy checks BEFORE this feeds the next stage ----
    print("\nCHECKS")
    dur  = df.groupby("flight_id")["time_s"].max() / 60
    drop = df.groupby("flight_id")["step_cost_pct"].sum()
    print(f"  Rows: {len(df)}   Flights: {df.flight_id.nunique()}")
    print(f"  Duration  : synthetic {dur.mean():.2f} min   SULEKO T20P 6.43 min")
    print(f"  Battery drop/flight: synthetic {drop.mean():.1f} %   SULEKO T20P 78.4 %")
    print(f"  Drain rate: synthetic {df.drain_pct_min.mean():.1f} %/min   SULEKO 12.2 %/min")
    heavy = df[df.liquid_L > 15].drain_pct_min.mean()
    light = df[df.liquid_L < 6].drain_pct_min.mean()
    print(f"  Heavy vs light drain: {heavy:.1f} vs {light:.1f} %/min  "
          f"(reduction {100*(heavy-light)/heavy:.1f} %)")
    print(f"  Slope mean {df.slope_deg.mean():.1f} deg (grid {grid.mean():.1f})")
    print(f"\nSaved: {out}")


if __name__ == "__main__":
    main()# synthetic_generator.py
# Component 3 - Synthetic flight telemetry from the calibrated energy model
#
# Every row is SYNTHETIC but anchored to real data:
#   - slopes   : sampled from the real SRTM slope grid of Ouvahkelle Estate
#   - physics  : calibrated energy model (fitted on Kenilworth telemetry)
#   - flights  : liquid load, duration and speed drawn from SULEKO statistics
#   - noise    : 9 % multiplicative noise = measured model error on SULEKO T20P
#
# Run:  cd ~/component3 && source venv/bin/activate
#       python3 data/synthetic_generator.py

import os, sys, json, glob
import numpy as np
import pandas as pd

BASE = os.environ.get("C3_BASE", os.path.expanduser("~/component3"))
sys.path.insert(0, f"{BASE}/energy_model")
from energy_model import EnergyModel

SEED        = 42
N_FLIGHTS   = 250          # SULEKO has 163 mountain flights; 250 gives variety
DT_S        = 2.0          # seconds between rows
NOISE_SD    = 0.09         # lognormal sigma = model error on SULEKO T20P
RTH_BATTERY = 20.0         # return-to-home threshold (%)


def load_model():
    m = EnergyModel()
    with open(f"{BASE}/energy_model/calibrated_model.json") as f:
        c = json.load(f)
    m.mass_empty_kg = c["mass_empty_kg"]
    m.battery_wh    = c["battery_wh_effective"]
    m.level_scale   = c["suleko_level_scale"]
    return m, c


def find_slope_grid():
    hits = glob.glob(f"{BASE}/**/slope_grid_srtm.npy", recursive=True)
    if not hits:
        raise FileNotFoundError("slope_grid_srtm.npy not found - run terrain_processor.py first")
    return np.load(hits[0]), hits[0]


def simulate_flight(model, grid, rng, fid):
    rows_, cols_ = grid.shape
    r, c   = rng.integers(0, rows_), rng.integers(0, cols_)
    liquid = rng.uniform(18.5, 20.5)
    flow   = liquid / rng.uniform(5.5, 7.0) / 60.0       # L/s, empties in ~6 min
    speed  = rng.normal(6.4, 0.8)                        # km/h, per-flight cruise
    battery, t, rows = 100.0, 0.0, []
    while liquid > 0.3 and battery > RTH_BATTERY:
        slope = float(grid[r, c])
        v_ms  = max(1.0, speed + rng.normal(0, 0.4)) / 3.6
        cost  = model.energy_cost(liquid, slope, v_ms, dt=DT_S)
        cost *= rng.lognormal(0, NOISE_SD)
        rows.append(dict(flight_id=fid, time_s=round(t, 1), row=r, col=c,
                         slope_deg=round(slope, 2), speed_ms=round(v_ms, 3),
                         liquid_L=round(liquid, 3),
                         mass_kg=round(model.current_mass(liquid), 2),
                         battery_pct=round(battery, 3),
                         step_cost_pct=round(cost, 5),
                         drain_pct_min=round(cost / DT_S * 60, 3)))
        battery -= cost
        liquid  -= flow * DT_S
        t       += DT_S
        # move to a neighbouring cell about every 10 s (random walk on the grid)
        if int(t) % 10 == 0:
            r = int(np.clip(r + rng.integers(-1, 2), 0, rows_ - 1))
            c = int(np.clip(c + rng.integers(-1, 2), 0, cols_ - 1))
    return rows


def main():
    rng = np.random.default_rng(SEED)
    model, const = load_model()
    grid, path = find_slope_grid()
    print(f"Slope grid: {path}  shape={grid.shape}  mean={grid.mean():.1f} deg")

    rows = []
    for fid in range(N_FLIGHTS):
        rows += simulate_flight(model, grid, rng, fid)
    df = pd.DataFrame(rows)
    df["source"] = "synthetic: calibrated energy model + SRTM slopes"
    out = f"{BASE}/data/synthetic_flights.csv"
    df.to_csv(out, index=False)

    # ---- accuracy checks BEFORE this feeds the next stage ----
    print("\nCHECKS")
    dur  = df.groupby("flight_id")["time_s"].max() / 60
    drop = df.groupby("flight_id")["step_cost_pct"].sum()
    print(f"  Rows: {len(df)}   Flights: {df.flight_id.nunique()}")
    print(f"  Duration  : synthetic {dur.mean():.2f} min   SULEKO T20P 6.43 min")
    print(f"  Battery drop/flight: synthetic {drop.mean():.1f} %   SULEKO T20P 78.4 %")
    print(f"  Drain rate: synthetic {df.drain_pct_min.mean():.1f} %/min   SULEKO 12.2 %/min")
    heavy = df[df.liquid_L > 15].drain_pct_min.mean()
    light = df[df.liquid_L < 6].drain_pct_min.mean()
    print(f"  Heavy vs light drain: {heavy:.1f} vs {light:.1f} %/min  "
          f"(reduction {100*(heavy-light)/heavy:.1f} %)")
    print(f"  Slope mean {df.slope_deg.mean():.1f} deg (grid {grid.mean():.1f})")
    print(f"\nSaved: {out}")


if __name__ == "__main__":
    main()