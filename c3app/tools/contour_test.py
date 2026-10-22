"""Do rows that follow the contour save energy? Run from c3app:  python3 tools/contour_test.py [n_fields]
For random test-set fields, score every row direction (0..165 deg, step 15) with the energy model and report
how the cheapest direction relates to the direction of the hill, and how much energy is at stake."""
import os, sys, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../backend")
import fields as F, train_agent as T, engine as G
from engine import Frame, Flight, Problem

n = int(sys.argv[1]) if len(sys.argv) > 1 else 12
mp = G.MissionPlanner()
z = T.tile()
rng = np.random.default_rng(7)
rows = []
for f in T.make_fields(z, 99, n, T.EVAL_COLS):
    par = dict(G.DEFAULTS); par["tank_l"] = f["tank_l"]
    P = Problem(f["z"], f["poly"], f["trees"], f["depot"], par, mp.model)
    gy, gx = np.gradient(P.z, G.GRID)            # note: z is indexed [x, y] like Problem.elev
    # uphill direction (deg, 0-180) averaged over the field, as a line direction in world x/y
    m = np.array([[G.point_in_poly((i + .5) * G.GRID, (j + .5) * G.GRID, P.poly) for j in range(P.z.shape[1])] for i in range(P.z.shape[0])])
    if not m.any(): continue
    ax, ay = gx[m].mean(), gy[m].mean()          # d z / d i  (world x),  d z / d j (world y)
    up = np.degrees(np.arctan2(ay, ax)) % 180    # row direction that points straight up the hill
    slope = np.degrees(np.arctan(np.hypot(gx[m], gy[m]))).mean()
    E = {}
    for th in range(0, 180, 15):
        fr = Frame(P, float(th)); fl = Flight(fr)
        try:
            e = min(sum((S := fl.run(fr.build(a, b, True), True))["sortie_e"].values()) + 1000. * S["contact"]
                    for a, b in ((0, 0), (0, 1), (1, 0), (1, 1)))
        except RuntimeError:
            continue
        E[th] = e
    if len(E) < 6: continue
    best = min(E, key=E.get)
    d = lambda a, b: min(abs(a - b) % 180, 180 - abs(a - b) % 180)
    ang_to_hill = d(best, up)                    # 0 = rows run straight up the hill, 90 = along the contour
    e_up = E[min(E, key=lambda t: d(t, up))]; e_ct = E[min(E, key=lambda t: d(t, (up + 90) % 180))]
    rows.append((slope, ang_to_hill, (max(E.values()) / min(E.values()) - 1) * 100, (e_up / E[best] - 1) * 100, (e_ct / E[best] - 1) * 100))
r = np.array(rows)
print(f"{len(r)} fields, mean slope {r[:,0].mean():.1f} deg")
print(f"cheapest row direction vs the hill: mean {r[:,1].mean():.0f} deg  (0 = up the hill, 90 = along the contour)")
print(f"  fields whose cheapest rows run closer to the contour than to the slope: {(r[:,1] > 45).sum()} of {len(r)}")
print(f"energy gap between the best and the worst direction: mean {r[:,2].mean():.1f} %  max {r[:,2].max():.1f} %")
print(f"rows straight up the hill cost {r[:,3].mean():.1f} % more than the best;  rows along the contour {r[:,4].mean():.1f} % more")
