"""How steep are the fields the agent trains on? Run from c3app:  python3 tools/slope_spread.py"""
import os, sys, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../backend")
import fields as F, train_agent as T
SIZE = getattr(F, "SIZE", None); GRID = getattr(F, "GRID", 5.0)

def slope_deg(z):
    gy, gx = np.gradient(z, GRID)
    return np.degrees(np.arctan(np.hypot(gx, gy)))

def inside(poly, n):
    xs = (np.arange(n) + .5) * GRID
    X, Y = np.meshgrid(xs, xs)
    m = np.zeros((n, n), bool)
    for i in range(n):
        for j in range(n):
            m[i, j] = F.in_poly((X[i, j], Y[i, j]), poly)
    return m

z = T.tile()
for name, cols in (("train (west 60%)", T.TRAIN_COLS), ("test (east 40%)", T.EVAL_COLS)):
    fl = T.make_fields(z, 123, 150, cols)
    med, p90, share = [], [], []
    for f in fl:
        s = slope_deg(f["z"]); m = inside(f["poly"], s.shape[0])
        v = s[m] if m.any() else s.ravel()
        med.append(np.median(v)); p90.append(np.percentile(v, 90)); share.append((v > 12).mean())
    med, p90, share = map(np.array, (med, p90, share))
    print(f"{name}: {len(fl)} fields")
    print(f"  median slope inside field: mean {med.mean():.1f} deg, 90th pct of fields {np.percentile(med,90):.1f}")
    print(f"  steepest 10% of ground:    mean {p90.mean():.1f} deg, max {p90.max():.1f}")
    print(f"  fields with >30% of area steeper than 12 deg: {(share>.3).sum()} of {len(fl)}")
