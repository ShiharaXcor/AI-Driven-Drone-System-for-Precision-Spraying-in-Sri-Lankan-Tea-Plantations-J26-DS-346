#!/usr/bin/env python3
"""
Phase 1 - can the EXISTING trained agents plan a route for a NEW estate?

What it does (plain words)
  1. Makes N new random tea fields (shape, trees, slope) from your real SRTM tile.
  2. Gives each field to the standard route planner (rows along the longest edge, tree arcs, full tanks).
  3. Gives the same field to each trained agent. The agent flies it step by step, exactly as it was trained,
     and a simple wrapper adds refills (fly home, reload 20 L, fly back to the nearest unsprayed ground).
  4. Scores both with the same energy model and the same coverage test, then compares them.

Run from ~/component3 with the venv active:
  python3 c3app/tools/phase1_existing_agent.py --models ppo_ext24_1000k_s2 --fields 5        (quick check)
  python3 c3app/tools/phase1_existing_agent.py --fields 40                                   (full test)
  python3 c3app/tools/phase1_existing_agent.py --list                                        (show your models)
"""
import os, sys, json, math, time, argparse, csv
import numpy as np
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "backend"))
import engine as EN              # planner machinery; it also loads tea_spray_env
import fields as F

E = EN.E
BASE = os.environ.get("C3_BASE", os.path.expanduser("~/component3"))
OUT = os.path.join(HERE, "..", "phase1_output")
E.PATCH_M = 300.0                # the new fields live in a 300 m window (agents were trained on 200 m patches)
DEFAULT_MODELS = ["ppo_ext24_1000k_s0", "ppo_ext24_1000k_s1", "ppo_ext24_1000k_s2", "ppo_ext24_crash100_1000k_s0"]
RESERVE = 15.0                   # battery % that must remain after flying home (same as the planner)


# ----------------------------------------------------------------------------- helpers
def load_tile():
    p = os.environ.get("C3_TILE")
    if p:
        return np.load(p)
    z, _ = E.load_elevation()
    return np.nan_to_num(z, nan=float(np.nanmean(z)))


def load_agent(name):
    from stable_baselines3 import PPO, SAC
    algo = SAC if name.startswith("sac") else PPO
    m = algo.load(os.path.join(BASE, "drl_agent", "models", name), device="cpu")
    mode = {16: "spec16", 24: "ext24", 26: "ext26"}[m.observation_space.shape[0]]
    return m, mode


def make_problem(f):
    par = dict(EN.DEFAULTS)
    par["tank_l"] = float(f["tank_l"])
    return EN.Problem(f["z"], f["poly"], f["trees"], f["depot"], par, E.load_model())


def run_standard(P):
    """the fair fixed route: rows along the longest edge, tree arcs, full tanks (last one trimmed)"""
    th = EN.longest_edge_deg(P.poly)
    fr = EN.Frame(P, th)
    fl = EN.Flight(fr)
    best = None
    for a, b in ((False, False), (False, True), (True, False), (True, True)):
        try:
            S = fl.run(fr.build(a, b, True), "trim")
        except RuntimeError:
            continue
        e = sum(S["sortie_e"].values()) + 1000.0 * S["contact"]
        if best is None or e < best[0]:
            best = (e, S)
    S = best[1]
    m = fl.metrics(S)
    return dict(energy=m["energy_pct"], coverage=m["coverage"], area_ha=m["area_ha"], contact=m["contact_steps"],
                sorties=m["sorties"], minutes=m["minutes"], ha_per_100=m["ha_per_100pct"])


def score_segments(P, seg):
    """same coverage test as Flight.coverage: a 2 m cell counts as sprayed if a spray point is within swath/2"""
    lo, hi = P.poly.min(0), P.poly.max(0)
    cx = np.arange(lo[0] + EN.COV_DX / 2, hi[0], EN.COV_DX)
    cy = np.arange(lo[1] + EN.COV_DX / 2, hi[1], EN.COV_DX)
    gx, gy = np.meshgrid(cx, cy, indexing="ij")
    cells = np.stack([gx.ravel(), gy.ravel()], 1)
    ok = EN.point_in_poly(cells[:, 0], cells[:, 1], P.poly)
    if len(P.trees):
        d = np.hypot(cells[:, None, 0] - P.trees[None, :, 0], cells[:, None, 1] - P.trees[None, :, 1])
        ok &= ~(d < P.rad[None, :]).any(1)
    if len(seg) == 0:
        return 0.0, 0.0
    seg = np.asarray(seg, float)
    L = np.hypot(seg[:, 2] - seg[:, 0], seg[:, 3] - seg[:, 1])
    ns = np.maximum(1, np.ceil(L / 1.0).astype(int))
    idx = np.repeat(np.arange(len(seg)), ns)
    j = np.arange(len(idx)) - np.repeat(np.cumsum(ns) - ns, ns)
    f = ((j + 0.5) / ns[idx])[:, None]
    pts = seg[idx, :2] * (1 - f) + seg[idx, 2:] * f
    dist, _ = cKDTree(pts).query(cells, distance_upper_bound=P.swath / 2)
    cov = np.isfinite(dist)
    return float((cov & ok).sum() / max(int(ok.sum()), 1)), float((cov & ok).sum() * EN.COV_DX ** 2 / 1e4)


# ----------------------------------------------------------------------------- the agent flies a field
def fly_agent(model, mode, P, hide_mass=False, max_steps=9000, max_sorties=99):
    env = E.TeaSprayEnv(obs_mode=mode, terminate_on_collision=False, transit=False, hide_mass=hide_mass)
    env.reset(seed=0)
    tank = P.tank
    # put the new field into the simulator: terrain, trees, and a coverage map where everything
    # outside the polygon (and inside tree canopies) already counts as done
    env.z = np.asarray(P.z, float).copy()
    env.trees = np.asarray(P.trees, float).reshape(-1, 2)
    env.tree_r = np.asarray(P.rad, float)
    gx, gy = env.cx, env.cy
    free = EN.point_in_poly(gx.ravel(), gy.ravel(), P.poly).reshape(gx.shape)
    for (tx, ty), r in zip(env.trees, env.tree_r):
        free &= ((gx - tx) ** 2 + (gy - ty) ** 2) > r * r
    env.covered = ~free
    n_target = int(free.sum())
    dep = np.asarray(P.depot, float)

    def home_cost(x, y, liq):
        d = max(float(np.hypot(x - dep[0], y - dep[1])), 1e-6)
        rise = max(P.home_alt - float(env._elev(x, y)), 0.0)
        return env._leg_cost(liq, math.degrees(math.atan2(rise, d)), d, E.TRANSIT_V)

    def enter_from(x, y):
        """fly from the depot (full tank) to the unsprayed cell nearest to (x, y)"""
        idx = np.where(~env.covered.ravel())[0]
        if len(idx) == 0:
            return None
        cxs, cys = gx.ravel()[idx], gy.ravel()[idx]
        k = int(np.argmin((cxs - x) ** 2 + (cys - y) ** 2))
        tx, ty = float(cxs[k]), float(cys[k])
        d = max(float(np.hypot(tx - dep[0], ty - dep[1])), 1e-6)
        rise = max(float(env._elev(tx, ty)) - P.home_alt, 0.0)
        cost = env._leg_cost(tank, math.degrees(math.atan2(rise, d)), d, E.TRANSIT_V)
        return tx, ty, cost

    energy, sorties, steps, contacts = 0.0, 1, 0, 0
    seg = []
    env.liquid, env.battery, env._allow, env.area_ha, env.t = tank, 100.0, 0.0, 0.0, 0
    first = enter_from(dep[0], dep[1])
    env.x, env.y, env.h, env.vx, env.vy = first[0], first[1], 3.0, 0.0, 0.0
    energy += first[2]
    env.battery -= first[2]
    obs = env._obs()
    start_left = int((~env.covered).sum())
    stalls, failed = 0, ""
    slog, s_steps, s_move, s_e0 = [], 0, 0, energy
    at_home = False
    while steps < max_steps:
        a, _ = model.predict(obs, deterministic=True)
        x0, y0, liq0, bat0 = env.x, env.y, env.liquid, env.battery
        obs, _, _, _, _ = env.step(a)
        steps += 1
        s_steps += 1
        s_move += int(math.hypot(env.x - x0, env.y - y0) > 0.3)
        energy += bat0 - env.battery
        if liq0 - env.liquid > 1e-9:
            seg.append((x0, y0, env.x, env.y))
        if env._min_gap() < E.COLLIDE_M:
            contacts += 1
        left = int((~env.covered).sum())
        if left <= 0.01 * n_target:
            break
        # end of sortie: tank empty, or not enough battery left to fly home with the reserve
        if env.liquid <= 0.05 or env.battery - 1.1 * home_cost(env.x, env.y, env.liquid) < RESERVE:
            energy += home_cost(env.x, env.y, env.liquid)
            at_home = True
            slog.append(dict(sortie=sorties, steps=s_steps, moving=s_move / max(s_steps, 1), gained_pct=100.0 * (start_left - left) / max(n_target, 1),
                             energy=energy - s_e0, liquid_left=env.liquid))
            if sorties >= max_sorties:
                break
            if start_left - left < 0.005 * n_target:
                stalls += 1
                if stalls >= 3:
                    failed = "agent made no progress for 3 sorties"
                    break
            else:
                stalls = 0
            lastx, lasty = env.x, env.y
            nxt = enter_from(lastx, lasty)
            if nxt is None:
                break
            sorties += 1
            env.liquid, env.battery = tank, 100.0 - nxt[2]
            energy += nxt[2]
            env.x, env.y, env.h, env.vx, env.vy = nxt[0], nxt[1], 3.0, 0.0, 0.0
            obs = env._obs()
            start_left = int((~env.covered).sum())
            s_steps, s_move, s_e0 = 0, 0, energy
            at_home = False
    else:
        failed = "step limit reached"
    if not at_home:
        energy += home_cost(env.x, env.y, env.liquid)       # fly home at the end
    cov, area = score_segments(P, seg)
    return dict(energy=energy, coverage=cov, area_ha=area, contact=contacts, sorties=sorties, steps=steps,
                ha_per_100=area * 100.0 / max(energy, 1e-9), failed=failed, slog=slog)


# ----------------------------------------------------------------------------- statistics
def bootstrap(x, n=4000, seed=0):
    x = np.asarray(x, float)
    rng = np.random.default_rng(seed)
    m = np.array([x[rng.integers(0, len(x), len(x))].mean() for _ in range(n)])
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def verdict(gain, lo, hi, cov):
    if cov < 0.95:
        return "INCOMPLETE: the agent leaves part of the field unsprayed, so it is not a fair route"
    if lo > 0:
        return "BETTER than the standard route (95% interval above zero)"
    if hi < 0:
        return "WORSE than the standard route (95% interval below zero)"
    return "NO CLEAR DIFFERENCE from the standard route"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="*", default=None)
    ap.add_argument("--fields", type=int, default=40)
    ap.add_argument("--seed", type=int, default=777)
    ap.add_argument("--trees", type=int, default=None, help="fixed number of trees per field (default: random 0-15)")
    ap.add_argument("--z-scale", type=float, default=1.0, help="terrain steepness factor (1.0 = as the real tile)")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    mdir = os.path.join(BASE, "drl_agent", "models")
    avail = sorted(f[:-4] for f in os.listdir(mdir) if f.endswith(".zip")) if os.path.isdir(mdir) else []
    if a.list:
        print("models in", mdir); [print("  ", m) for m in avail]; return
    names = a.models or [m for m in DEFAULT_MODELS if m in avail]
    names = [n for n in names if n in avail] or [n for n in avail if "ext24" in n and "blind" not in n and "nomass" not in n][:3]
    if not names:
        sys.exit(f"no trained models found in {mdir}")
    print("models:", names)
    os.makedirs(OUT, exist_ok=True)
    z = load_tile()
    rng = np.random.default_rng(a.seed)
    fields = [F.random_field(z, rng, tank=20.0, z_scale=a.z_scale, rough_m=0.0, trees=a.trees) for _ in range(a.fields)]
    print(f"{len(fields)} new fields | tank 20 L | terrain scale {a.z_scale} | trees {'random 0-15' if a.trees is None else a.trees}")
    t0 = time.time()
    base = []
    for i, f in enumerate(fields):
        base.append(run_standard(make_problem(f)))
    print(f"standard routes done in {time.time() - t0:.0f}s | mean energy {np.mean([b['energy'] for b in base]):.0f}% "
          f"| mean sorties {np.mean([b['sorties'] for b in base]):.1f} | contacts {sum(b['contact'] for b in base)}")
    summary = {}
    rows = []
    for name in names:
        model, mode = load_agent(name)
        res = []
        t1 = time.time()
        for i, f in enumerate(fields):
            r = fly_agent(model, mode, make_problem(f), hide_mass="blind" in name)
            res.append(r)
            print(f"  {name} field {i + 1}/{len(fields)}: coverage {r['coverage'] * 100:.0f}%  "
                  f"efficiency {r['ha_per_100']:.3f} ha/100% (standard {base[i]['ha_per_100']:.3f})  contacts {r['contact']}"
                  f"{'  [' + r['failed'] + ']' if r['failed'] else ''}", flush=True)
            rows.append(dict(model=name, field=i, trees=len(f["trees"]), ha=poly_ha(f), **{f"agent_{k}": v for k, v in r.items() if k != "slog"},
                             **{f"std_{k}": v for k, v in base[i].items()}))
        gain = np.array([(r["ha_per_100"] / b["ha_per_100"] - 1.0) * 100.0 for r, b in zip(res, base)])
        lo, hi = bootstrap(gain)
        cov = float(np.mean([r["coverage"] for r in res]))
        summary[name] = dict(gain_mean_pct=float(gain.mean()), ci95=[lo, hi], win_rate=float((gain > 0.5).mean()),
                             loss_rate=float((gain < -0.5).mean()), mean_agent_coverage=cov,
                             mean_std_coverage=float(np.mean([b["coverage"] for b in base])),
                             agent_contacts=int(sum(r["contact"] for r in res)),
                             agent_mean_sorties=float(np.mean([r["sorties"] for r in res])),
                             failed=int(sum(bool(r["failed"]) for r in res)), verdict=verdict(gain.mean(), lo, hi, cov),
                             seconds=time.time() - t1)
    print("\n" + "=" * 78)
    print("PHASE 1 RESULT: existing agent vs standard route on NEW fields")
    print("gain = change in hectares sprayed per 100% battery (positive = agent is more efficient)")
    print("=" * 78)
    for n, s in summary.items():
        print(f"{n}\n   gain {s['gain_mean_pct']:+.1f}%  95% interval [{s['ci95'][0]:+.1f}, {s['ci95'][1]:+.1f}]  "
              f"wins {s['win_rate'] * 100:.0f}%  losses {s['loss_rate'] * 100:.0f}%\n   coverage: agent {s['mean_agent_coverage'] * 100:.0f}% "
              f"vs standard {s['mean_std_coverage'] * 100:.0f}% | tree contacts {s['agent_contacts']} | "
              f"failed fields {s['failed']}/{len(fields)}\n   -> {s['verdict']}")
    json.dump(dict(settings=vars(a), models=names, summary=summary), open(os.path.join(OUT, "phase1_summary.json"), "w"), indent=1, default=float)
    with open(os.path.join(OUT, "phase1_per_field.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print("\nsaved:", os.path.abspath(os.path.join(OUT, "phase1_summary.json")))
    print("saved:", os.path.abspath(os.path.join(OUT, "phase1_per_field.csv")))


def poly_ha(f):
    return EN.poly_area(np.asarray(f["poly"], float)) / 1e4


if __name__ == "__main__":
    main()
