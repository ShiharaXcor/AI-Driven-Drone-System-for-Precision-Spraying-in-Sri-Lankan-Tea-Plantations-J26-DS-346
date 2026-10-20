# export_routes.py
# Component 3 - record the actual flights of the fixed routes and the trained DRL agents on ONE patch,
# for the 3D viewer.  Same JSON layout as planner.py, so one viewer reads both.
#
# Run (from ~/component3, venv active):
#   python3 drl_agent/export_routes.py --seed 5003 --models ppo_ext24_1000k_s2 ppo_blind_ext24_1000k_s0
#
# Writes planner_output/routes_<seed>.json : terrain, trees, home, and for every route the path with
# height, tank level and battery at every second, plus area / battery / collisions / coverage per charge.

import os, sys, json, argparse
import numpy as np

BASE = os.environ.get("C3_BASE", os.path.expanduser("~/component3"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tea_spray_env as E
from tea_spray_env import TeaSprayEnv, LawnmowerPolicy
from compare import DetourLawnmower, load_agent


def fly(env, act, seed):
    obs, _ = env.reset(seed=seed)
    x, y, alt, liq, bat = [], [], [], [], []

    def snap():
        x.append(env.x); y.append(env.y)
        alt.append(float(env._elev(env.x, env.y) + env.h)); liq.append(env.liquid); bat.append(env.battery)
    snap()
    done, info = False, {}
    while not done:
        obs, r, term, trunc, info = env.step(act(obs))
        snap()
        done = term or trunc
    seg = dict(kind="spray", sortie=1, x=np.round(x, 2).tolist(), y=np.round(y, 2).tolist(),
               alt=np.round(alt, 2).tolist(), liq=np.round(liq, 3).tolist(), bat=np.round(bat, 3).tolist())
    row = dict(area_ha=float(info["area_ha"]), battery_used=float(info["battery_used"]),
               collisions=int(info["collisions"]), crashed=bool(info["collisions"] > 0),
               ha_per_charge=float(info["coverage_per_charge"]), path_m=float(env.path_m), steps=int(env.t))
    return [seg], row


def find_seeds(models, trees, first, n):
    """patches where the plain lawnmower hits a tree but the agent flies clean at about the same efficiency"""
    model, mode = load_agent(models[0])
    kw = dict(hide_mass=True) if "blind" in models[0] else {}
    plain = TeaSprayEnv(terminate_on_collision=False); pol = LawnmowerPolicy()
    det_env = TeaSprayEnv(terminate_on_collision=True); dp = DetourLawnmower()
    ag = TeaSprayEnv(terminate_on_collision=True, obs_mode=mode, **kw)
    good = []
    for s in range(first, first + n):
        pol.reset(); dp.reset()
        a = E.run_episode(plain, lambda o: pol.act(plain), s)
        d = E.run_episode(det_env, lambda o: dp.act(det_env), s)
        g = E.run_episode(ag, lambda o: model.predict(o, deterministic=True)[0], s)
        ok = a["collisions"] > 0 and g["collisions"] == 0 and d["collisions"] == 0
        if ok:
            gain = (g["coverage_per_charge"] / d["coverage_per_charge"] - 1) * 100
            good.append((gain, s, a["collisions"], g["coverage_per_charge"]))
    good.sort(reverse=True)
    print(f"seeds with {trees} trees where the plain lawnmower hit a tree, the detour route and the agent did not:")
    for gain, s, c, cpc in good[:8]:
        print(f"  seed {s}: lawnmower contacts {c}, agent {cpc:.3f} ha/charge ({gain:+.1f}% vs detour)")
    if not good:
        print("  none found - try more patches (--n) or a different model")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trees", type=int, default=None, help="trees per patch (training used 8)")
    ap.add_argument("--find", action="store_true", help="search for good demo seeds instead of exporting (needs --models)")
    ap.add_argument("--first", type=int, default=5000)
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--seed", type=int, default=5003)
    ap.add_argument("--models", nargs="*", default=[])
    ap.add_argument("--out", default=f"{BASE}/planner_output")
    a = ap.parse_args()
    if a.trees is not None:
        E.N_TREES = a.trees
    if a.find:
        find_seeds(a.models, a.trees or 8, a.first, a.n)
        return
    plans, rows = {}, {}
    pol = LawnmowerPolicy(); e = TeaSprayEnv(terminate_on_collision=False); pol.reset()
    plans["lawnmower (fixed route)"], rows["lawnmower (fixed route)"] = fly(e, lambda o: pol.act(e), a.seed)
    dp = DetourLawnmower(); e2 = TeaSprayEnv(terminate_on_collision=True); dp.reset()
    plans["lawnmower + detour"], rows["lawnmower + detour"] = fly(e2, lambda o: dp.act(e2), a.seed)
    for nm in a.models:
        model, mode = load_agent(nm)
        kw = dict(hide_mass=True) if "blind" in nm else {}
        env = TeaSprayEnv(terminate_on_collision=True, obs_mode=mode, **kw)
        plans[f"DRL agent: {nm}"], rows[f"DRL agent: {nm}"] = fly(env, lambda o: model.predict(o, deterministic=True)[0], a.seed)
    e.reset(seed=a.seed)
    base = rows["lawnmower + detour"]["ha_per_charge"]
    for r in rows.values():
        r["vs_detour_pct"] = (r["ha_per_charge"] / base - 1) * 100
    out = dict(seed=a.seed, field=[0, 0, 200, 200], home=[5.0, 5.0],
               terrain=dict(dx=E.TERRAIN_DX, z=np.round(e.z, 2).tolist()),
               trees=[dict(x=float(t[0]), y=float(t[1]), r=float(r)) for t, r in zip(e.trees, e.tree_r)],
               summary=rows, plans=plans, settings=dict(tank_l=E.LIQUID_L, swath_m=E.SWATH_M))
    os.makedirs(a.out, exist_ok=True)
    p = f"{a.out}/routes_{a.seed}.json"
    json.dump(out, open(p, "w"))
    print(f"{'route':48s} {'ha/charge':>9s} {'area ha':>8s} {'battery %':>9s} {'collisions':>10s} {'vs detour':>9s}")
    for k, r in rows.items():
        print(f"{k:48s} {r['ha_per_charge']:9.3f} {r['area_ha']:8.3f} {r['battery_used']:9.1f} {r['collisions']:10d} {r['vs_detour_pct']:+8.1f}%")
    print(f"\nSaved {p}  ({os.path.getsize(p) / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()