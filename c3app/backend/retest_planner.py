"""Planner-only check under an energy scenario (no trained agent needed): usual route vs search planner, hectares per 100 % battery.
Run:  C3_SCENARIO=a05 python3 retest_planner.py --set test --n 20"""
import os, sys, json, time, argparse
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import agent_env as A, fields as F
from eval_agent import metrics_of, bootstrap
from train_agent import tile, EVAL_COLS
import energy_scenario as ES
ap = argparse.ArgumentParser(); ap.add_argument("--set", default="test"); ap.add_argument("--n", type=int, default=20); ap.add_argument("--seed", type=int, default=9000)
a = ap.parse_args()
kw = dict(test={}, tank20=dict(tank=20.0), tank40=dict(tank=40.0), steep=dict(z_scale=1.6))[a.set]
z = tile(); rng = np.random.default_rng(a.seed)
fields = [F.random_field(z, rng, cols=EVAL_COLS, **kw) for _ in range(a.n)]
g = []; t = time.time()
for f in fields:
    P = A.make_problem(f); _, S, th = A.run_standard(P); s = metrics_of(P, S, th)
    b = A.run_planner(P); p = metrics_of(P, b[1], b[2]); g.append((p["eff"] / s["eff"] - 1) * 100)
g = np.array(g); lo, hi = bootstrap(g)
out = dict(scenario=ES.settings()[0] or "saved model", set=a.set, n=a.n, planner_gain_mean=float(g.mean()), planner_gain_median=float(np.median(g)), ci=[lo, hi], wins=int((g > .5).sum()), secs=round(time.time() - t))
print(json.dumps(out))
