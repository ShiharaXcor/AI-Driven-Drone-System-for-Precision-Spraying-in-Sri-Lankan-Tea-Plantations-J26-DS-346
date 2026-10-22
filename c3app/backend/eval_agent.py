"""Fair evaluation of a trained mission agent against the standard route and the search planner.
Everything is scored the same way: hectares actually sprayed per 100 % battery (coverage counted),
plus tree contacts. Positive 'gain' = more efficient than the standard route."""
import os, sys, json, time, argparse
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import agent_env as A
import fields as F
from engine import Frame, Flight
from stable_baselines3 import PPO, SAC


def metrics_of(P, S, th):
    fl = Flight(Frame(P, float(th)))
    m = fl.metrics(S)
    return dict(energy=m["energy_pct"], coverage=m["coverage"], area=m["area_ha"], contact=m["contact_steps"],
                sorties=m["sorties"], eff=m["ha_per_100pct"], minutes=m["minutes"])


def agent_route(model, f, hide_mass=False, safe=True):
    if safe:
        env = A.plan_with_agent(model, f, hide_mass)
    else:
        env = A.MissionEnv(fixed_fields=[f], hide_mass=hide_mass)
        o, _ = env.reset()
        done, info = False, {}
        while not done:
            a, _ = model.predict(o, deterministic=True)
            o, r, done, _, info = env.step(a)
        if info.get("failed") or not hasattr(env, "S"):
            env = None
    if env is None:
        return None, None
    return metrics_of(env.P, env.S, env.design[0]), env


def bootstrap(x, n=4000, seed=0):
    x = np.asarray(x, float); rng = np.random.default_rng(seed)
    m = np.array([x[rng.integers(0, len(x), len(x))].mean() for _ in range(n)])
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def evaluate(model, fields, with_planner=True, hide_mass=False, log=print):
    rows = []
    for i, f in enumerate(fields):
        P = A.make_problem(f)
        e_std, S_std, th_std = A.run_standard(P)
        std = metrics_of(P, S_std, th_std)
        ag, env = agent_route(model, f, hide_mass)
        pl = None
        if with_planner:
            b = A.run_planner(P)
            pl = metrics_of(P, b[1], b[2])
        rows.append(dict(i=i, trees=len(f["trees"]), tank=f["tank_l"], z_scale=f.get("z_scale", 1.0), std=std, agent=ag, planner=pl,
                         design=None if ag is None else env.design, fills=None if ag is None else [round(x, 1) for x in env.fills]))
        log(f"  field {i + 1}/{len(fields)} trees {len(f['trees']):2d} tank {f['tank_l']:.0f}: std {std['eff']:.3f}  "
            f"agent {'FAILED' if ag is None else format(ag['eff'], '.3f') + ' cov ' + format(ag['coverage'] * 100, '.0f') + '% sorties ' + str(ag['sorties']) + ' min ' + format(ag['minutes'], '.0f') + ' contacts ' + str(ag['contact'])}"
            f"  (std sorties {std['sorties']}, {std['minutes']:.0f} min)  planner {'-' if pl is None else format(pl['eff'], '.3f')}")
    return rows


def summarise(rows):
    ok = [r for r in rows if r["agent"] is not None]
    out = dict(n=len(rows), failed=len(rows) - len(ok))
    if not ok:
        return out
    ga = np.array([(r["agent"]["eff"] / r["std"]["eff"] - 1) * 100 for r in ok])
    lo, hi = bootstrap(ga)
    out.update(agent_gain_mean=float(ga.mean()), agent_gain_median=float(np.median(ga)), agent_gain_ci=[lo, hi],
               wins=int((ga > 0.5).sum()), losses=int((ga < -0.5).sum()),
               agent_cov=float(np.mean([r["agent"]["coverage"] for r in ok])), std_cov=float(np.mean([r["std"]["coverage"] for r in ok])),
               agent_contacts=int(sum(r["agent"]["contact"] for r in ok)), fields_with_contact=int(sum(r["agent"]["contact"] > 0 for r in ok)),
               agent_minutes_ratio=float(np.mean([r["agent"]["minutes"] / r["std"]["minutes"] for r in ok])), agent_sorties_mean=float(np.mean([r["agent"]["sorties"] for r in ok])), std_sorties_mean=float(np.mean([r["std"]["sorties"] for r in ok])), std_contacts=int(sum(r["std"]["contact"] for r in ok)))
    if all(r["planner"] for r in ok):
        gp = np.array([(r["planner"]["eff"] / r["std"]["eff"] - 1) * 100 for r in ok])
        out.update(planner_gain_mean=float(gp.mean()), planner_gain_median=float(np.median(gp)), planner_cov=float(np.mean([r["planner"]["coverage"] for r in ok])),
                   agent_vs_planner_mean=float(np.mean([(r["agent"]["eff"] / r["planner"]["eff"] - 1) * 100 for r in ok])))
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True); ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--set", default="test", help="test | tank20 | tank40 | trees15 | steep | rough")
    ap.add_argument("--seed", type=int, default=9000)
    ap.add_argument("--no-planner", action="store_true")
    a = ap.parse_args()
    from train_agent import tile, EVAL_COLS
    z = tile()
    rng = np.random.default_rng(a.seed)
    kw = dict(test={}, tank20=dict(tank=20.0), tank40=dict(tank=40.0), trees15=dict(trees=15), steep=dict(z_scale=1.6), rough=dict(rough_m=3.0))[a.set]
    fields = [F.random_field(z, rng, cols=EVAL_COLS, **kw) for _ in range(a.n)]
    path = a.model if os.path.exists(a.model) else os.path.join(HERE, "..", "agents", a.model)
    Algo = SAC if os.path.basename(path).startswith("sac") else PPO
    model = Algo.load(path, device="cpu")
    t = time.time()
    rows = evaluate(model, fields, not a.no_planner)
    s = summarise(rows)
    print(json.dumps(s, indent=1))
    os.makedirs(os.path.join(HERE, "..", "agents"), exist_ok=True)
    json.dump(dict(set=a.set, summary=s, rows=rows), open(os.path.join(HERE, "..", "agents", f"eval_{os.path.basename(path)}_{a.set}{__import__('energy_scenario').tag()}.json"), "w"), default=float)
    print("seconds", round(time.time() - t))
