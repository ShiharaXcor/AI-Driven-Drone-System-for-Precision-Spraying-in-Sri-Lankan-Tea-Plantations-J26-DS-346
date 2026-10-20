# compare.py
# Component 3 - fair, statistical comparison of dynamic (DRL) routing against fixed routes.
#
# Run (from ~/component3, venv active):
#   python3 drl_agent/compare.py --models ppo_ext24_1000k_s2 ppo_ext24_crash100_1000k_s0 --patches 200
#   python3 drl_agent/compare.py --models ppo_ext24_crash100_1000k_s0 --patches 100 --trees 8 16
#
# Fixed routes compared against:
#   lawnmower        : the plain serpentine sweep. It has NO obstacle avoidance and flies through
#                      tree canopies (every contact step is counted as a collision).
#   lawnmower+detour : the SAME serpentine sweep, but with a simple local side-step around any tree
#                      the sensor sees ahead (same 15 m sensor as the agent). This is the fair
#                      fixed-route opponent: a pilot or planner would not fly through trees.
# For each trained agent it reports, on fresh patches never used for training:
#   coverage per charge, area, collisions, crash rate, and the paired difference against both
#   baselines with a 95% bootstrap confidence interval and the win rate.

import os, sys, json, argparse
import numpy as np

BASE = os.environ.get("C3_BASE", os.path.expanduser("~/component3"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tea_spray_env as E
from tea_spray_env import TeaSprayEnv, LawnmowerPolicy, run_episode


class DetourLawnmower(LawnmowerPolicy):
    """Lawnmower sweep plus a local side-step around trees the sensor can see."""
    MARGIN = 3.5          # keep at least this far from a canopy edge (m)

    def act(self, env):
        a = super().act(env)
        d = a[:2] / max(np.hypot(a[0], a[1]), 1e-9)
        push = np.zeros(2)
        for (tx, ty), r in zip(env.trees, env.tree_r):
            cx, cy = tx - env.x, ty - env.y
            dist = np.hypot(cx, cy)
            if dist > E.SENSE_M + r:
                continue
            along = cx * d[0] + cy * d[1]
            lat = d[0] * cy - d[1] * cx              # >0: tree is to the left of the heading
            clear = r + self.MARGIN
            if along > -r and abs(lat) < clear:
                right = np.array([d[1], -d[0]])
                side = right if lat >= 0 else -right
                w = (1.0 - abs(lat) / clear) * (1.0 - min(max(along, 0.0), E.SENSE_M) / E.SENSE_M * 0.6)
                push += side * w
        v = d + 2.5 * push
        n = max(np.hypot(v[0], v[1]), 1e-9)
        return np.array([v[0] / n, v[1] / n, 0.0])


def load_agent(name):
    from stable_baselines3 import PPO, SAC
    Algo = SAC if name.startswith("sac") else PPO
    m = Algo.load(f"{BASE}/drl_agent/models/{name}", device="cpu")
    n_obs = m.observation_space.shape[0]
    mode = {16: "spec16", 24: "ext24", 26: "ext26"}[n_obs]
    return m, mode


def ep(env, fn, seed):
    """one episode + dose-corrected coverage: new ground is credited at most SWATH x path length,
    i.e. never at less than the real dose (litres per metre is fixed, so a wiggly path cannot get extra credit)"""
    info = dict(run_episode(env, fn, seed))
    info["path_m"] = float(env.path_m)
    info["area_dc"] = min(info["area_ha"], E.SWATH_M * env.path_m / 1e4)
    info["cpc_dc"] = info["area_dc"] * 100.0 / max(info["battery_used"], 1e-6)
    return info


def run_all(seeds, agent_names):
    out = {}
    pol = LawnmowerPolicy()
    env_plain = TeaSprayEnv(terminate_on_collision=False)
    out["lawnmower"] = []
    for s in seeds:
        pol.reset()
        out["lawnmower"].append(ep(env_plain, lambda o: pol.act(env_plain), s))
    dpol = DetourLawnmower()
    env_det = TeaSprayEnv(terminate_on_collision=True)
    out["lawnmower+detour"] = []
    for s in seeds:
        dpol.reset()
        out["lawnmower+detour"].append(ep(env_det, lambda o: dpol.act(env_det), s))
    for nm in agent_names:
        model, mode = load_agent(nm)
        kw = dict(hide_mass=True) if "blind" in nm else {}      # blind models were trained with the mass hidden
        if "nomass" in nm:
            raise SystemExit(f"{nm}: trained in a different world (energy ignores mass) - not comparable here")
        env = TeaSprayEnv(terminate_on_collision=True, obs_mode=mode, **kw)
        out[nm] = [ep(env, lambda o: model.predict(o, deterministic=True)[0], s) for s in seeds]
    return out


def col(rs, k):
    return np.array([r[k] for r in rs], dtype=float)


def boot_ci(a, b, n=2000, seed=0):
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(a), size=(n, len(a)))
    g = (a[idx].mean(1) / b[idx].mean(1) - 1.0) * 100.0
    return float(np.percentile(g, 2.5)), float(np.percentile(g, 97.5))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--patches", type=int, default=200)
    ap.add_argument("--first-seed", type=int, default=6000, help="fresh patch seeds (training used other seeds)")
    ap.add_argument("--trees", type=int, nargs="+", default=[8], help="tree counts per patch (training used 8)")
    a = ap.parse_args()

    seeds = list(range(a.first_seed, a.first_seed + a.patches))
    os.makedirs(f"{BASE}/compare_output", exist_ok=True)
    summary = {}
    for nt in a.trees:
        E.N_TREES = nt
        print(f"\n{'=' * 92}\n{a.patches} fresh patches, {nt} trees per patch\n{'=' * 92}")
        res = run_all(seeds, a.models)
        cpc = {k: col(v, "coverage_per_charge") for k, v in res.items()}
        print(f"{'route':34s} {'ha/charge':>9s} {'area ha':>8s} {'battery %':>9s} {'collisions':>10s} {'crash rate':>10s}")
        for k, v in res.items():
            print(f"{k:34s} {cpc[k].mean():9.3f} {col(v, 'area_ha').mean():8.3f} {col(v, 'battery_used').mean():9.1f} "
                  f"{col(v, 'collisions').mean():10.2f} {100 * (col(v, 'collisions') > 0).mean():9.0f}%")
        print("\nPaired change in coverage per charge (95% bootstrap CI over patches; win = agent better on that patch)")
        rows = {}
        for nm in a.models:
            for base in ("lawnmower", "lawnmower+detour"):
                g = (cpc[nm].mean() / cpc[base].mean() - 1) * 100
                lo, hi = boot_ci(cpc[nm], cpc[base])
                win = 100 * (cpc[nm] > cpc[base]).mean()
                verdict = "better" if lo > 0 else ("worse" if hi < 0 else "no clear difference")
                print(f"  {nm:30s} vs {base:17s}: {g:+6.1f}%  [{lo:+5.1f}, {hi:+5.1f}]  wins {win:3.0f}%  -> {verdict}")
                rows[f"{nm} vs {base}"] = dict(change_pct=g, ci_low=lo, ci_high=hi, win_pct=win, verdict=verdict)
        cdc = {k: col(v, "cpc_dc") for k, v in res.items()}
        print("\nDOSE-CORRECTED (new ground credited at most 6 m x path length = the real spray dose; the number to quote)")
        print(f"{'route':34s} {'eff.swath m':>11s} {'ha/charge':>9s}")
        for k, v in res.items():
            print(f"{k:34s} {np.mean(col(v, 'area_ha') * 1e4 / col(v, 'path_m')):11.2f} {cdc[k].mean():9.3f}")
        for nm in a.models:
            for base in ("lawnmower", "lawnmower+detour"):
                g = (cdc[nm].mean() / cdc[base].mean() - 1) * 100
                lo, hi = boot_ci(cdc[nm], cdc[base])
                verdict = "better" if lo > 0 else ("worse" if hi < 0 else "no clear difference")
                print(f"  {nm:30s} vs {base:17s}: {g:+6.1f}%  [{lo:+5.1f}, {hi:+5.1f}]  -> {verdict}")
                rows[f"DOSE-CORRECTED {nm} vs {base}"] = dict(change_pct=g, ci_low=lo, ci_high=hi, verdict=verdict)
        summary[f"trees_{nt}"] = dict(
            routes={k: dict(ha_per_charge=float(cpc[k].mean()), area_ha=float(col(v, "area_ha").mean()),
                            battery_used=float(col(v, "battery_used").mean()),
                            collisions=float(col(v, "collisions").mean()),
                            crash_rate=float((col(v, "collisions") > 0).mean())) for k, v in res.items()},
            paired=rows)
    json.dump(dict(patches=a.patches, first_seed=a.first_seed, results=summary),
              open(f"{BASE}/compare_output/compare.json", "w"), indent=2)
    print(f"\nSaved: {BASE}/compare_output/compare.json")


if __name__ == "__main__":
    main()