"""Compare, on the same unseen test fields (east 40 % of the terrain), the routes that matter for the claim:
  usual (standard) | search planner | flat-first rule | agent version 1 | agent version 2 (chooses the strip order)
Saving = battery saved against the usual route, scored by the same energy model. A route that touches a tree counts as -50.
Run from c3app/backend:  python3 compare_v2.py --v2 mission_ppo_v2_s0 [--v1 mission_ppo_s0] [--blind-v2 name] [--n 30]"""
import os, sys, argparse, collections
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import agent_env as A1, agent_env_v2 as A2, train_agent as T, flatfirst as FF
from stable_baselines3 import PPO

ap = argparse.ArgumentParser()
ap.add_argument("--v2", required=True); ap.add_argument("--v1", default=None); ap.add_argument("--blind-v2", default=None)
ap.add_argument("--n", type=int, default=30); ap.add_argument("--seed", type=int, default=9000)
a = ap.parse_args()
AG = os.path.join(HERE, "..", "agents")
load = lambda n: PPO.load(os.path.join(AG, n + ".zip"), device="cpu")
models = {"agent v2": (load(a.v2), A2, False)}
if a.v1: models["agent v1"] = (load(a.v1), A1, False)
if a.blind_v2: models["agent v2 blind"] = (load(a.blind_v2), A2, True)

def agent_energy(model, mod, blind, f):
    env = A1.plan_with_agent(model, f, hide_mass=blind, env_cls=mod.MissionEnv)
    if env is None: return None, None
    e = sum(env.S["sortie_e"].values())
    return (e if env.S["contact"] == 0 else None), env

rows = collections.defaultdict(list); use = collections.Counter()
for k, f in enumerate(T.make_fields(T.tile(), a.seed, a.n, T.EVAL_COLS)):
    P = A1.make_problem(f)
    e_std, S_std, th_std = A1.run_standard(P)
    pl = A1.run_planner(P, coarse=True)
    if pl is None: continue
    e_pl, _, th, fr_, fd = pl
    ff = FF.flat_first(P, float(th), (fr_, fd), True)
    res = {"search planner": e_pl, "flat-first rule": min(ff["e_best"], e_pl)}
    for name, (m, mod, blind) in models.items():
        e, env = agent_energy(m, mod, blind, f)
        res[name] = e
        if name == "agent v2" and env is not None: use[A2.ORDER_NAMES[getattr(env, "mode", 0)]] += 1
    for name, e in res.items():
        rows[name].append(-50.0 if e is None else (1 - e / e_std) * 100)
    print(f"field {k + 1}/{a.n}", flush=True)
print(f"\nBattery saved against the usual route on {len(rows['search planner'])} unseen fields (a tree contact counts -50)")
print(f"{'route':18s} {'mean %':>8s} {'median %':>9s}")
for name, v in rows.items():
    v = np.array(v); print(f"{name:18s} {v.mean():8.2f} {np.median(v):9.2f}")
if "agent v2" in rows:
    v2 = np.array(rows["agent v2"])
    for other in [n for n in rows if n not in ("agent v2",)]:
        d = v2 - np.array(rows[other]); print(f"agent v2 minus {other:16s}: mean {d.mean():+.2f}  better on {(d > .05).sum()}, worse on {(d < -.05).sum()} fields")
print("strip order chosen by agent v2:", dict(use))
