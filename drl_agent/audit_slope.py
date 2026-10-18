# audit_slope.py
# Component 3 - audit of (1) the slope angles and (2) the energy equations.
#
# Run (from ~/component3, venv active):   python3 drl_agent/audit_slope.py
#
# 1. Recomputes slope from the SRTM elevation with the standard GIS method (Horn, 3x3)
#    and with a plain gradient, and compares them with the saved slope_grid_srtm.npy.
#    If the saved grid is a constant factor steeper, the cell spacing used was wrong.
# 2. Shows how SRTM noise and grid resolution change the apparent slope.
# 3. Shows how much the slope actually matters to the energy model.
# 4. Checks the energy equations against physics (hover power ~ mass^1.5) and prints the
#    fitted parameters so they can be compared with the aircraft datasheet.

import os, sys, glob, json
import numpy as np
from scipy.ndimage import sobel, gaussian_filter

BASE = os.environ.get("C3_BASE", os.path.expanduser("~/component3"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
CELL = 30.0                                  # SRTM 1 arc-second, about 30 m


def find(name):
    hits = glob.glob(f"{BASE}/**/{name}", recursive=True)
    return hits[0] if hits else None


def stats(a, name):
    a = a[~np.isnan(a)]
    print(f"  {name:36s} mean {a.mean():5.1f}  median {np.median(a):5.1f}  p90 {np.percentile(a, 90):5.1f}"
          f"  max {a.max():5.1f}  >30deg {100 * (a > 30).mean():4.1f}%")


def main():
    pz, ps = find("elevation_srtm.npy"), find("slope_grid_srtm.npy")
    z = np.load(pz).astype(float)
    zf = np.nan_to_num(z, nan=np.nanmean(z))
    print(f"\nElevation: {pz}\n  {z.shape[0]} x {z.shape[1]} cells = {z.shape[0]*CELL:.0f} x {z.shape[1]*CELL:.0f} m, "
          f"{np.nanmin(z):.0f}-{np.nanmax(z):.0f} m, {int(np.isnan(z).sum())} missing")

    print("\n1) SLOPE ANGLES (degrees)")
    gy, gx = np.gradient(zf, CELL)
    ref = np.degrees(np.arctan(np.hypot(gx, gy)))
    horn = np.degrees(np.arctan(np.hypot(sobel(zf, axis=1) / (8 * CELL), sobel(zf, axis=0) / (8 * CELL))))
    stats(ref, "recomputed, plain gradient")
    stats(horn, "recomputed, Horn 3x3 (standard)")
    if ps:
        s = np.load(ps).astype(float)
        stats(s, "SAVED slope_grid_srtm.npy")
        if s.shape == ref.shape:
            ok = np.hypot(gx, gy) > 0.05
            ratio = np.tan(np.radians(s))[ok] / np.hypot(gx, gy)[ok]
            r = float(np.median(ratio))
            print(f"  tan(saved) / tan(recomputed) = {r:.2f}  (should be about 1.00)")
            if abs(r - 1) > 0.08:
                print(f"  -> WARNING: the saved grid behaves as if the cell size were {CELL / r:.1f} m instead of {CELL:.0f} m."
                      f"\n     Check the pixel size used in terrain_processor.py. Mean slope would be ~{ref.mean():.0f} deg, not {s.mean():.0f} deg.")
            else:
                print("  -> saved grid agrees with the recomputation.")
        else:
            print(f"  (saved grid shape {s.shape} differs from elevation {z.shape}; compare means only)")

    print("\n2) HOW MUCH THE DATA ITSELF INFLATES SLOPE (illustrative)")
    rng = np.random.default_rng(0)
    truth = gaussian_filter(zf, 1.0)

    def msl(a, c=CELL):
        g1, g0 = np.gradient(a, c)
        return float(np.degrees(np.arctan(np.hypot(g0, g1))).mean())
    for sd in (0, 3, 6, 9):
        print(f"  surface + {sd} m random vertical error -> mean slope {np.mean([msl(truth + rng.normal(0, sd, truth.shape)) for _ in range(20)]):.1f} deg")
    k = 3
    r_, c_ = (zf.shape[0] // k) * k, (zf.shape[1] // k) * k
    z90 = zf[:r_, :c_].reshape(r_ // k, k, c_ // k, k).mean(axis=(1, 3))
    print(f"  same terrain averaged to 90 m cells      -> mean slope {msl(z90, 90.0):.1f} deg  (resolution matters)")

    print("\n3) DOES SLOPE MATTER TO ENERGY?  (half tank, 6.4 km/h)")
    from tea_spray_env import load_model
    m = load_model()
    flat = m.drain_at(10, 0, 6.4)
    for sl in (0, 10, 20, 30, 40):
        d = m.drain_at(10, sl, 6.4)
        print(f"  slope {sl:2d} deg: {d:5.2f} %/min  ({(d / flat - 1) * 100:+.1f}% vs flat)")
    print("  -> a 10 deg error in slope changes the drain by only about 2%.")

    print("\n4) ENERGY EQUATIONS")
    cal = json.load(open(f"{BASE}/energy_model/calibrated_model.json"))
    m0, E = cal["mass_empty_kg"], cal["battery_wh_effective"]
    mf, ml = m0 + 18.8, m0 + 6.0
    print(f"  Fitted empty mass {m0:.1f} kg (with battery?), effective battery energy {E:.0f} Wh, "
          f"SULEKO level scale {cal['suleko_level_scale']:.3f}")
    print(f"  Hover power ~ mass^1.5: predicted drain ratio full/low = {(mf / ml) ** 1.5:.3f}, measured 18/11 = {18 / 11:.3f}")
    print(f"  Hover power: {m.hover_power(m.current_mass(20)):.0f} W (full 20 L)  vs  {m.hover_power(m.current_mass(0)):.0f} W (empty)")
    print("  NOTE: mass and battery energy are fitted to two Kenilworth points (two unknowns), so the fit itself is not a test.")
    print("  The independent tests are the SULEKO T25 flights (6.4% error). Compare the fitted mass and Wh with the datasheet")
    print("  of the aircraft in the Kenilworth video; a large mismatch means the two parameters are absorbing something else.")


if __name__ == "__main__":
    main()