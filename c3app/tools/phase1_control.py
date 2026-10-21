#!/usr/bin/env python3
"""
Phase 1 control test - is the agent weak, or is my test wrapper unfair to it?

Same wrapper, same scoring, but the field is the SHAPE THE AGENT WAS TRAINED ON:
a plain 180 x 180 m square, 8 trees, refill point at a corner, on your real terrain.
If the agent does well here but fails on the random polygons, the problem is generalisation (the agent).
If it fails here too, the wrapper is the problem and the Phase 1 result cannot be trusted yet.

Run from ~/component3 (venv active):
  python3 c3app/tools/phase1_control.py --models ppo_ext24_1000k_s2 --fields 5
"""
import os, sys, argparse
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import phase1_existing_agent as T
import fields as F

SQUARE = np.array([[60, 60], [240, 60], [240, 240], [60, 240]], float)


def square_field(z_tile, rng, n_trees):
    f = F.random_field(z_tile, rng, tank=20.0, z_scale=1.0, rough_m=0.0, trees=0)
    f["poly"] = SQUARE.copy()
    f["trees"] = F.random_trees(rng, SQUARE, n_trees)
    f["depot"] = np.array([50.0, 50.0])
    return f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="*", default=["ppo_ext24_1000k_s2"])
    ap.add_argument("--fields", type=int, default=5)
    ap.add_argument("--trees", type=int, default=8)
    ap.add_argument("--seed", type=int, default=4242)
    a = ap.parse_args()
    z = T.load_tile()
    rng = np.random.default_rng(a.seed)
    fields = [square_field(z, rng, a.trees) for _ in range(a.fields)]
    base = [T.run_standard(T.make_problem(f)) for f in fields]
    print(f"{len(fields)} square 180x180 m fields, {a.trees} trees | standard: mean sorties {np.mean([b['sorties'] for b in base]):.1f}, "
          f"coverage {np.mean([b['coverage'] for b in base]) * 100:.0f}%, {np.mean([b['ha_per_100'] for b in base]):.3f} ha/100%")
    for name in a.models:
        model, mode = T.load_agent(name)
        res = []
        for i, f in enumerate(fields):
            r = T.fly_agent(model, mode, T.make_problem(f), hide_mass="blind" in name)
            res.append(r)
            print(f"  {name} field {i + 1}: coverage {r['coverage'] * 100:.0f}%  {r['ha_per_100']:.3f} ha/100%  sorties {r['sorties']}  "
                  f"contacts {r['contact']}{'  [' + r['failed'] + ']' if r['failed'] else ''}", flush=True)
        gain = np.mean([(r['ha_per_100'] / b['ha_per_100'] - 1) * 100 for r, b in zip(res, base)])
        print(f"CONTROL {name}: coverage {np.mean([r['coverage'] for r in res]) * 100:.0f}% | "
              f"{np.mean([r['ha_per_100'] for r in res]):.3f} ha/100% vs standard {np.mean([b['ha_per_100'] for b in base]):.3f} | "
              f"gain {gain:+.1f}% | contacts {sum(r['contact'] for r in res)}")


if __name__ == "__main__":
    main()
