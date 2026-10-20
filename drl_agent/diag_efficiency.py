# diag_efficiency.py
# Component 3 - WHERE does the agent's gain come from?  (area per tank, path length, litres, battery)
#
# Run (from ~/component3, venv active):
#   python3 drl_agent/diag_efficiency.py --models ppo_ext24_1000k_s2 ppo_blind_ext24_1000k_s0 --patches 60
#
# Why: in compare.py the agent sprays more area (0.408-0.413 ha vs 0.386) for almost the same battery (73-74 %).
# A straight sweep with a 6 m swath cannot cover more than about 6 m x path length.  This script prints the
# "effective swath" = area / path length for every route.  If the agent's number is clearly above ~6 m, the gain
# comes from how the simulator counts coverage (turn geometry, grid cells, no dose-uniformity check), not from
# saving energy, and the claim must be worded accordingly.

import os, sys, argparse
import numpy as np

BASE = os.environ.get("C3_BASE", os.path.expanduser("~/component3"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tea_spray_env as E
from tea_spray_env import TeaSprayEnv, LawnmowerPolicy, run_episode
from compare import DetourLawnmower, load_agent


def collect(env, fn, seeds, reset=None):
    rows = []
    for s in seeds:
        if reset:
            reset()
        run_episode(env, fn, s)
        used = 100.0 - env.battery
        rows.append((env.area_ha, env.path_m, E.LIQUID_L - env.liquid, used))
    return np.array(rows)


def show(name, r):
    area, path, liq, bat = r.T
    eff = area * 1e4 / path
    print(f"{name:30s} {area.mean():7.3f} {path.mean():8.0f} {liq.mean():8.2f} {eff.mean():9.2f} "
          f"{liq.sum() / area.sum():8.1f} {bat.mean():8.1f} {bat.mean() / path.mean() * 1000:9.1f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="*", default=[])
    ap.add_argument("--patches", type=int, default=60)
    a = ap.parse_args()
    seeds = list(range(6000, 6000 + a.patches))
    print(f"{'route':30s} {'area ha':>7s} {'path m':>8s} {'litres':>8s} {'eff.swath m':>9s} {'L per ha':>8s} {'batt %':>8s} {'batt%/km':>9s}")
    pol = LawnmowerPolicy(); e1 = TeaSprayEnv(terminate_on_collision=False)
    show("lawnmower", collect(e1, lambda o: pol.act(e1), seeds, pol.reset))
    dp = DetourLawnmower(); e2 = TeaSprayEnv(terminate_on_collision=True)
    show("lawnmower+detour", collect(e2, lambda o: dp.act(e2), seeds, dp.reset))
    for nm in a.models:
        model, mode = load_agent(nm)
        kw = dict(hide_mass=True) if "blind" in nm else {}
        env = TeaSprayEnv(terminate_on_collision=True, obs_mode=mode, **kw)
        show(nm, collect(env, lambda o: model.predict(o, deterministic=True)[0], seeds))
    print(f"\nA straight 6 m swath gives at most {E.SWATH_M:.1f} m of new ground per metre flown.")


if __name__ == "__main__":
    main()