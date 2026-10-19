# demo.py
# Component 3 - demonstration of every novel component, end to end, on one real patch.
#
#   1. Mass- and slope-aware energy model (calibrated on Kenilworth, validated on SULEKO)
#   2. Real terrain (SRTM elevation -> slope) used by the simulator
#   3. DRL navigation agent (PPO/SAC) flying the patch with obstacle avoidance
#   4. Comparison with the fixed lawnmower route on the SAME patch and trees
#
# Run (from ~/component3, venv active):
#   python3 drl_agent/demo.py                      # picks a saved model automatically
#   python3 drl_agent/demo.py --model ppo_ext24_crash100_1000k_s0 --seed 5003
#   python3 drl_agent/demo.py --model ppo_ext26_transit_crash100_best_lrd_2000k_s0
# Output: demo_output/ (3 figures, summary.json) and a checklist printed in the terminal.

import os, sys, json, glob, re, argparse
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

BASE = os.environ.get("C3_BASE", os.path.expanduser("~/component3"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tea_spray_env import TeaSprayEnv, LawnmowerPolicy, load_model, PATCH_M, WARN_M, COLLIDE_M
from stable_baselines3 import PPO, SAC

OUT = f"{BASE}/demo_output"
PREFERRED = ["ppo_ext24_1000k_s2", "ppo_ext24_crash100_1000k_s0", "ppo_ext24_1000k_s0"]
KENILWORTH = [(18.8, 18.0), (6.0, 11.0)]          # (litres, measured drain %/min) at 12 deg, 8.7 km/h


# ---------------------------------------------------------------- helpers
def find_model(name):
    d = f"{BASE}/drl_agent/models"
    for n in ([name] if name else PREFERRED):
        if os.path.exists(f"{d}/{n}.zip"):
            return n
    zips = sorted(glob.glob(f"{d}/*.zip"), key=os.path.getmtime)
    return os.path.basename(zips[-1])[:-4] if zips else None


def settings_from(name, model):
    obs_mode = {16: "spec16", 24: "ext24", 26: "ext26"}[model.observation_space.shape[0]]
    m = re.search(r"_v(\d+(?:\.\d+)?)", name)
    return dict(obs_mode=obs_mode, v_max_kmh=float(m.group(1)) if m else 6.4,
                transit="transit" in name, use_mass="nomass" not in name)


def fly(env, act_fn, seed):
    env.reset(seed=seed)
    obs = env._obs()
    rec = dict(x=[env.x], y=[env.y], battery=[env.battery], liquid=[env.liquid],
               area=[0.0], gap=[env._min_gap()])
    done, info = False, {}
    while not done:
        obs, _, te, tr, info = env.step(act_fn(obs))
        done = te or tr
        rec["x"].append(env.x); rec["y"].append(env.y); rec["battery"].append(env.battery)
        rec["liquid"].append(env.liquid); rec["area"].append(env.area_ha)
        rec["gap"].append(env._min_gap())
    return {k: np.array(v) for k, v in rec.items()}, info


def summarise(rec, info, env):
    return dict(area_ha=float(info["area_ha"]), battery_used=float(info["battery_used"]),
                coverage_per_charge=float(info["coverage_per_charge"]),
                collisions=int(info["collisions"]), min_tree_gap_m=float(rec["gap"].min()),
                steps=int(len(rec["x"]) - 1), liquid_left=float(info["liquid_left"]),
                outbound_pct=float(info.get("transit_out_pct", 0.0)),
                return_pct=float(info.get("return_pct", 0.0)))


# ---------------------------------------------------------------- component 1: energy model
def energy_checks(m):
    res = {}
    sc = m.level_scale
    m.level_scale = 1.0                                   # Kenilworth fit, before the SULEKO level scale
    res["kenilworth_fit"] = [(L, real, m.drain_at(L, 12, 8.7)) for L, real in KENILWORTH]
    m.level_scale = sc                                    # what the simulator actually uses
    res["kenilworth"] = [(L, real, m.drain_at(L, 12, 8.7)) for L, real in KENILWORTH]
    res["level_scale"] = sc
    full, empty = m.drain_at(20, 0, 6.4), m.drain_at(0, 0, 6.4)
    res["mass_effect_pct"] = (full / empty - 1) * 100
    res["drain_full"], res["drain_empty"] = full, empty
    flat, steep = m.drain_at(10, 0, 6.4), m.drain_at(10, 30, 6.4)
    res["slope_effect_pct"] = (steep / flat - 1) * 100
    cal = json.load(open(f"{BASE}/energy_model/calibrated_model.json"))
    res["suleko"] = cal.get("validation", cal.get("suleko_validation", None))
    return res


def fig_energy(m, path):
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    L = np.linspace(0, 20, 60)
    sc = m.level_scale
    m.level_scale = 1.0
    for s, c in ((0, "#1b9e77"), (12, "#d95f02"), (25, "#7570b3")):
        ax[0].plot(L, [m.drain_at(l, s, 8.7) for l in L], color=c, label=f"slope {s}° (Kenilworth fit)")
    m.level_scale = sc
    ax[0].plot(L, [m.drain_at(l, 12, 8.7) for l in L], color="#d95f02", ls="--",
               label=f"12° with SULEKO level scale {sc:.3f} (simulator)")
    ax[0].scatter([k[0] for k in KENILWORTH], [k[1] for k in KENILWORTH], color="black", zorder=5,
                  label="Kenilworth measured (12°)")
    ax[0].set_xlabel("liquid in tank (L)"); ax[0].set_ylabel("battery drain (%/min)")
    ax[0].set_title("Weight effect: a lighter drone drains slower"); ax[0].legend(frameon=False)
    S = np.linspace(0, 40, 50)
    for l, c in ((20, "#d95f02"), (10, "#1b9e77"), (2, "#7570b3")):
        ax[1].plot(S, [m.drain_at(l, s, 6.4) for s in S], color=c, label=f"{l} L")
    ax[1].set_xlabel("terrain slope (°)"); ax[1].set_ylabel("battery drain (%/min)")
    ax[1].set_title("Slope effect (small: hovering dominates)"); ax[1].legend(frameon=False)
    for a in ax:
        a.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(); fig.savefig(path, dpi=160); plt.close(fig)


# ---------------------------------------------------------------- component 2/3/4: mission figures
def fig_routes(envs, recs, sums, titles, path):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.6))
    for ax, env, rec, sm, ttl in zip(axes, envs, recs, sums, titles):
        im = ax.imshow(env.z.T, origin="lower", extent=[0, PATCH_M, 0, PATCH_M], cmap="terrain", alpha=0.85)
        ax.imshow(np.where(env.covered.T, 1.0, np.nan), origin="lower", extent=[0, PATCH_M, 0, PATCH_M],
                  cmap="Greens", vmin=0, vmax=1.6, alpha=0.55)
        for (tx, ty), r in zip(env.trees, env.tree_r):
            ax.add_patch(Circle((tx, ty), r, color="#7a1f1f", zorder=4))
            ax.add_patch(Circle((tx, ty), r + WARN_M, fill=False, ls=":", lw=0.8, color="#7a1f1f", zorder=4))
        ax.plot(rec["x"], rec["y"], color="black", lw=0.9, zorder=5)
        ax.scatter([rec["x"][0]], [rec["y"][0]], color="white", edgecolor="black", s=45, zorder=6)
        ax.scatter([rec["x"][-1]], [rec["y"][-1]], color="red", s=30, zorder=6)
        ax.set_xlim(0, PATCH_M); ax.set_ylim(0, PATCH_M); ax.set_aspect("equal")
        ax.set_title(f"{ttl}\n{sm['area_ha']:.3f} ha, battery {sm['battery_used']:.0f}%, "
                     f"{sm['coverage_per_charge']:.3f} ha/charge, collisions {sm['collisions']}", fontsize=10)
        ax.set_xlabel("east (m)"); ax.set_ylabel("north (m)")
    cb = fig.colorbar(im, ax=axes, fraction=0.025, pad=0.02); cb.set_label("elevation (m, real SRTM)")
    fig.suptitle("Same real terrain patch and same trees: green = sprayed, red discs = trees "
                 "(dotted = 3 m warning), white dot = start, red dot = end", fontsize=9.5)
    fig.savefig(path, dpi=160, bbox_inches="tight"); plt.close(fig)


def fig_traces(recs, titles, path):
    fig, ax = plt.subplots(1, 3, figsize=(13, 3.6))
    cols = ("#555555", "#d95f02")
    for rec, t, c in zip(recs, titles, cols):
        ax[0].plot(rec["battery"], color=c, label=t)
        ax[1].plot(rec["liquid"], color=c, label=t)
        ax[2].plot(rec["area"], color=c, label=t)
    for a, yl in zip(ax, ("battery (%)", "liquid (L)", "area sprayed (ha)")):
        a.set_xlabel("time (s)"); a.set_ylabel(yl); a.spines[["top", "right"]].set_visible(False)
    ax[0].legend(frameon=False)
    fig.tight_layout(); fig.savefig(path, dpi=160); plt.close(fig)


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=None, help="model name in drl_agent/models (without .zip)")
    ap.add_argument("--seed", type=int, default=5003, help="held-out patch seed (5000-5029 = test patches)")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)

    name = find_model(a.model)
    if name is None:
        sys.exit("No trained model found in drl_agent/models - run train.py first.")
    Algo = SAC if name.startswith("sac") else PPO
    model = Algo.load(f"{BASE}/drl_agent/models/{name}", device="cpu")
    kw = settings_from(name, model)
    print(f"\nModel: {name}   settings: {kw}   patch seed: {a.seed}")

    # 1. energy model
    em = load_model()
    e = energy_checks(em)
    fig_energy(em, f"{OUT}/1_energy_model.png")

    # 2-4. fly both policies on the same patch
    env_b = TeaSprayEnv(terminate_on_collision=False, **kw)
    env_a = TeaSprayEnv(terminate_on_collision=True, **kw)
    pol = LawnmowerPolicy(); pol.reset()
    rec_b, info_b = fly(env_b, lambda o: pol.act(env_b), a.seed)
    rec_a, info_a = fly(env_a, lambda o: model.predict(o, deterministic=True)[0], a.seed)
    sb, sa = summarise(rec_b, info_b, env_b), summarise(rec_a, info_a, env_a)
    titles = ("Fixed lawnmower route", f"DRL agent ({name})")
    fig_routes((env_b, env_a), (rec_b, rec_a), (sb, sa), titles, f"{OUT}/2_routes_on_real_terrain.png")
    fig_traces((rec_b, rec_a), ("lawnmower", "DRL agent"), f"{OUT}/3_mission_traces.png")

    # terrain facts for the slide
    slope_here = np.array([[env_a._slope_mag(x, y) for x in np.arange(5, PATCH_M, 10)]
                           for y in np.arange(5, PATCH_M, 10)])
    elev = (float(env_a.z.min()), float(env_a.z.max()))

    # ---- console checklist
    gain = (sa["coverage_per_charge"] / sb["coverage_per_charge"] - 1) * 100
    k = e["kenilworth"]
    print("\n" + "=" * 78)
    print("NOVELTY COMPONENT CHECK")
    print("=" * 78)
    print("1) Mass- and slope-aware energy model")
    for (L, real, raw), (_, _, pred) in zip(e["kenilworth_fit"], k):
        print(f"     Kenilworth {L:>4.1f} L : measured {real:.1f} %/min | fitted model {raw:.1f} "
              f"({abs(raw-real)/real*100:.1f}% off) | with SULEKO scale {pred:.1f}")
    print(f"     (SULEKO level scale {e['level_scale']:.3f} adjusts for the different aircraft/estate; "
          f"validated 6.4% on independent flat T25 flights)")
    print(f"     Weight effect (full vs empty tank, flat, 6.4 km/h): {e['drain_full']:.1f} vs "
          f"{e['drain_empty']:.1f} %/min  ({e['mass_effect_pct']:+.0f}%)")
    print(f"     Slope effect (0 to 30 deg, half tank): {e['slope_effect_pct']:+.1f}%  (small - hover dominates)")
    print("2) Real terrain used")
    print(f"     SRTM file: {env_a.z_path}")
    print(f"     This patch: elevation {elev[0]:.0f}-{elev[1]:.0f} m, mean slope {slope_here.mean():.1f} deg, "
          f"max {slope_here.max():.1f} deg, {len(env_a.trees)} trees")
    print("3) DRL agent with obstacle avoidance (same patch, same trees)")
    print(f"     {'':22}{'lawnmower':>12}{'agent':>12}")
    for key, lab, fmt in (("area_ha", "area sprayed (ha)", "{:.3f}"), ("battery_used", "battery used (%)", "{:.1f}"),
                          ("coverage_per_charge", "ha per charge", "{:.3f}"), ("collisions", "collisions", "{}"),
                          ("min_tree_gap_m", "closest tree gap (m)", "{:.1f}"), ("steps", "flight time (s)", "{}")):
        print(f"     {lab:22}{fmt.format(sb[key]):>12}{fmt.format(sa[key]):>12}")
    if kw["transit"]:
        print(f"     whole mission: outbound {sa['outbound_pct']:.1f}% + return {sa['return_pct']:.1f}% battery included")
    print(f"4) Change vs lawnmower on this patch: {gain:+.1f}% coverage per charge "
          f"(one patch only - see the 30-patch evaluation for the real result)")
    print("=" * 78)
    print(f"Figures + summary saved in: {OUT}")
    json.dump(dict(model=name, settings=kw, seed=a.seed, energy=e, lawnmower=sb, agent=sa,
                   gain_pct=gain, elevation_range=elev, mean_slope=float(slope_here.mean())),
              open(f"{OUT}/summary.json", "w"), indent=2, default=str)


if __name__ == "__main__":
    main()