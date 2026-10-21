#!/usr/bin/env python3
"""
Phase 1 diagnosis - WHERE does the agent lose its efficiency?

Three checks on one agent:
  A. NATIVE      : the agent in the exact simulator it was trained in (200 m patch, 8 trees, one sortie).
  B. REPLICA     : my wrapper, first sortie only, on a field built to look like that training patch.
                   If B is close to A, the wrapper is fair.
  C. FULL MISSION: my wrapper, all sorties, same field, with a line per sortie
                   (steps, how much of the time it moved, how much new ground it covered, battery used).

Run from ~/component3 (venv active):
  python3 c3app/tools/phase1_diagnose.py --model ppo_ext24_1000k_s2
"""
import os, sys, argparse
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import phase1_existing_agent as T
import fields as F

E = T.E
PATCH = np.array([[2, 2], [198, 2], [198, 198], [2, 198]], float)


def native(model, mode, seeds, hide_mass):
    E.PATCH_M = 200.0
    out = []
    for s in seeds:
        env = E.TeaSprayEnv(obs_mode=mode, terminate_on_collision=False, transit=False, hide_mass=hide_mass)
        obs, _ = env.reset(seed=1000 + s)
        done, info = False, {}
        while not done:
            a, _ = model.predict(obs, deterministic=True)
            obs, r, te, tr, info = env.step(a)
            done = te or tr
        out.append(info)
    E.PATCH_M = 300.0
    return out


def replica_field(z, rng):
    f = F.random_field(z, rng, tank=20.0, z_scale=1.0, rough_m=0.0, trees=0)
    f["poly"] = PATCH.copy()
    ts = F.random_trees(rng, PATCH, 8)
    f["trees"] = [t for t in ts if np.hypot(t["x"] - 5, t["y"] - 5) > 12]
    f["depot"] = np.array([1.0, 1.0])
    return f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="ppo_ext24_1000k_s2")
    ap.add_argument("--n", type=int, default=3)
    a = ap.parse_args()
    model, mode = T.load_agent(a.model)
    hide = "blind" in a.model
    z = T.load_tile()

    print("=" * 78)
    print("A. NATIVE (the simulator the agent was trained in)")
    for i, info in enumerate(native(model, mode, range(a.n), hide)):
        print(f"   seed {i}: area {info['area_ha']:.3f} ha | battery used {info['battery_used']:.0f}% | "
              f"{info['coverage_per_charge']:.3f} ha per 100% battery | collisions {info['collisions']}")

    rng = np.random.default_rng(99)
    fields = [replica_field(z, rng) for _ in range(a.n)]
    print("\nB. REPLICA (my wrapper, first sortie only, training-like field)")
    for i, f in enumerate(fields):
        r = T.fly_agent(model, mode, T.make_problem(f), hide_mass=hide, max_sorties=1)
        print(f"   field {i}: area {r['area_ha']:.3f} ha | energy {r['energy']:.0f}% | {r['ha_per_100']:.3f} ha per 100% battery | "
              f"contacts {r['contact']} | steps {r['steps']}")

    print("\nC. FULL MISSION on replica field 0, sortie by sortie")
    r = T.fly_agent(model, mode, T.make_problem(fields[0]), hide_mass=hide)
    for s in r["slog"]:
        print(f"   sortie {s['sortie']:2d}: {s['steps']:4d} steps | moving {s['moving'] * 100:3.0f}% of the time | "
              f"new ground {s['gained_pct']:5.1f}% of field | battery used {s['energy']:5.1f}% | liquid left {s['liquid_left']:.1f} L")
    print(f"   total: coverage {r['coverage'] * 100:.0f}% | {r['ha_per_100']:.3f} ha per 100% | {r['failed'] or 'finished'}")
    print("=" * 78)
    print("HOW TO READ: if A and B are close (within about 20%), the wrapper is fair. In C, a sortie with")
    print("'new ground' near 0 and 'moving' near 0 means the agent hovers; low 'moving' with some ground means it dithers.")


if __name__ == "__main__":
    main()
