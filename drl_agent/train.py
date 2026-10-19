# train.py
# Component 3 - train PPO or SAC on the tea-spray environment, log to MLflow,
# then evaluate on held-out patches against the fixed lawnmower route.
#
# Options: --obs spec16|ext24|ext26  --vmax <km/h>  --transit  --crash <penalty>
#          --no-mass    world ablation: the energy model ignores payload (tank always half full)
#          --hide-mass  agent ablation: the physics keeps the real payload, but the agent's
#                       observation no longer shows liquid / total mass / drain estimate
# Examples (from ~/component3, venv active):
#   python3 drl_agent/train.py --algo ppo --timesteps 200000
#   python3 drl_agent/train.py --algo sac --timesteps 100000
#   python3 drl_agent/train.py --algo ppo --timesteps 200000 --no-mass     # world ablation
#   python3 drl_agent/train.py --algo ppo --obs ext24 --timesteps 1000000 --hide-mass   # agent ablation

import os, sys, json, time, argparse
import numpy as np
import pandas as pd

BASE = os.environ.get("C3_BASE", os.path.expanduser("~/component3"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tea_spray_env import TeaSprayEnv, LawnmowerPolicy, run_episode

from stable_baselines3 import PPO, SAC
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.callbacks import BaseCallback, CallbackList

try:
    import mlflow
except ImportError:
    mlflow = None

EVAL_SEEDS = list(range(5000, 5030))      # held-out patches, never used for training


class LogCallback(BaseCallback):
    """Write one row per finished episode to CSV (and MLflow)."""
    def __init__(self, csv_path, use_mlflow):
        super().__init__()
        self.csv_path, self.use_mlflow, self.rows, self.n = csv_path, use_mlflow, [], 0

    def _on_step(self):
        for info, done in zip(self.locals["infos"], self.locals["dones"]):
            if done:
                self.n += 1
                row = dict(episode=self.n, timestep=self.num_timesteps,
                           reward=info["episode"]["r"], length=info["episode"]["l"],
                           coverage_per_charge=info.get("coverage_per_charge", np.nan),
                           area_ha=info.get("area_ha", np.nan),
                           battery_used=info.get("battery_used", np.nan),
                           collisions=info.get("collisions", 0))
                self.rows.append(row)
                if self.use_mlflow and self.n % 20 == 0:
                    mlflow.log_metrics({k: float(v) for k, v in row.items()
                                        if k not in ("episode", "timestep")},
                                       step=self.num_timesteps)
        return True

    def _on_training_end(self):
        pd.DataFrame(self.rows).to_csv(self.csv_path, index=False)


class BestCheckpoint(BaseCallback):
    """Every `freq` steps play 10 fixed validation patches with the deterministic policy
    and keep the weights with the highest mean episode reward.  Training can peak and then
    drift; this keeps the peak.  The validation patches (seeds 7000-7009) are separate from
    the 30 test patches, so the final test stays untouched."""
    VAL_SEEDS = list(range(7000, 7010))

    def __init__(self, env_kw, path, freq=100_000):
        super().__init__()
        self.env_kw, self.path, self.freq = env_kw, path, freq
        self.best, self.next, self.curve, self.env = -np.inf, freq, [], None

    def _score(self):
        if self.env is None:
            self.env = TeaSprayEnv(**self.env_kw)
        tot = []
        for s in self.VAL_SEEDS:
            obs, _ = self.env.reset(seed=s)
            done, r_sum = False, 0.0
            while not done:
                a, _ = self.model.predict(obs, deterministic=True)
                obs, r, te, tr, _ = self.env.step(a)
                r_sum += r
                done = te or tr
            tot.append(r_sum)
        return float(np.mean(tot))

    def _check(self):
        sc = self._score()
        self.curve.append((self.num_timesteps, sc))
        if sc > self.best:
            self.best = sc
            self.model.save(self.path)

    def _on_step(self):
        if self.num_timesteps >= self.next:
            self.next += self.freq
            self._check()
        return True

    def _on_training_end(self):
        self._check()


def evaluate(model, use_mass, obs_mode="spec16", **kw):
    """`kw` may contain hide_mass. It reaches both environments, which is harmless for the
    lawnmower (it ignores observations) and keeps the agent's evaluation world identical
    to its training world."""
    agent, base = [], []
    env_a = TeaSprayEnv(terminate_on_collision=True, use_mass=use_mass, obs_mode=obs_mode, **kw)
    env_b = TeaSprayEnv(terminate_on_collision=False, use_mass=use_mass, obs_mode=obs_mode, **kw)
    pol = LawnmowerPolicy()
    for s in EVAL_SEEDS:
        agent.append(run_episode(env_a, lambda o: model.predict(o, deterministic=True)[0], s))
        pol.reset()
        base.append(run_episode(env_b, lambda o: pol.act(env_b), s))
    def summ(rs):
        return dict(coverage_per_charge=float(np.mean([r["coverage_per_charge"] for r in rs])),
                    area_ha=float(np.mean([r["area_ha"] for r in rs])),
                    battery_used=float(np.mean([r["battery_used"] for r in rs])),
                    collisions=float(np.mean([r["collisions"] for r in rs])),
                    crash_rate=float(np.mean([r["collisions"] > 0 for r in rs])))
    return summ(agent), summ(base)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--algo", choices=["ppo", "sac"], default="ppo")
    ap.add_argument("--timesteps", type=int, default=100_000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--no-mass", action="store_true",
                    help="world ablation: energy ignores m(t) (tank treated as half full)")
    ap.add_argument("--hide-mass", action="store_true",
                    help="agent ablation: observation hides payload mass, physics unchanged")
    ap.add_argument("--obs", choices=["spec16", "ext24", "ext26"], default="spec16")
    ap.add_argument("--vmax", type=float, default=6.4, help="spraying speed cap, km/h")
    ap.add_argument("--transit", action="store_true", help="include base->field->base legs")
    ap.add_argument("--crash", type=float, default=20.0, help="crash penalty")
    ap.add_argument("--best", action="store_true", help="keep the best validation checkpoint")
    ap.add_argument("--val-every", type=int, default=100_000, help="steps between validations")
    ap.add_argument("--lr-decay", action="store_true", help="linearly lower the learning rate")
    ap.add_argument("--name", default=None)
    a = ap.parse_args()

    if a.no_mass and a.hide_mass:
        ap.error("--no-mass and --hide-mass cannot be combined: with --no-mass the payload "
                 "has no effect on the physics, so there is nothing left to hide")

    use_mass = not a.no_mass
    tag = (("_nomass" if a.no_mass else "") + ("_blind" if a.hide_mass else "")
           + ("" if a.obs == "spec16" else f"_{a.obs}")
           + ("" if a.vmax == 6.4 else f"_v{a.vmax:g}") + ("_transit" if a.transit else "")
           + ("" if a.crash == 20.0 else f"_crash{a.crash:g}")
           + ("_best" if a.best else "") + ("_lrd" if a.lr_decay else ""))
    name = a.name or f"{a.algo}{tag}_{a.timesteps//1000}k_s{a.seed}"
    # kw reaches the training env, evaluate(), the BestCheckpoint env, MLflow and eval.json
    kw = dict(v_max_kmh=a.vmax, transit=a.transit, r_crash=a.crash, hide_mass=a.hide_mass)
    out = f"{BASE}/drl_agent/runs/{name}"
    os.makedirs(out, exist_ok=True)
    os.makedirs(f"{BASE}/drl_agent/models", exist_ok=True)

    env = Monitor(TeaSprayEnv(seed=a.seed, use_mass=use_mass, obs_mode=a.obs, **kw),
                  info_keywords=("coverage_per_charge", "area_ha", "battery_used", "collisions"))
    common = dict(seed=a.seed, device="cpu", verbose=0)
    lr = (lambda p: 3e-4 * (0.1 + 0.9 * p)) if a.lr_decay else 3e-4     # p: 1 -> 0 over training
    if a.algo == "ppo":
        model = PPO("MlpPolicy", env, n_steps=2048, batch_size=256, learning_rate=lr,
                    gamma=0.995, gae_lambda=0.95, ent_coef=0.0, **common)
    else:
        model = SAC("MlpPolicy", env, learning_rate=lr, buffer_size=200_000,
                    learning_starts=5_000, batch_size=256, gamma=0.995, **common)

    use_mlflow = mlflow is not None
    if use_mlflow:
        mlflow.set_tracking_uri(f"sqlite:///{BASE}/mlflow.db")
        mlflow.set_experiment("component3-routing")
        mlflow.start_run(run_name=name)
        mlflow.log_params(dict(algo=a.algo, timesteps=a.timesteps, seed=a.seed,
                               use_mass=use_mass, obs=a.obs, **kw))
    cb = LogCallback(f"{out}/train_log.csv", use_mlflow)

    print(f"Training {name} ...")
    t0 = time.time()
    best_path = f"{out}/best_checkpoint"
    callbacks = cb
    if a.best:
        best_cb = BestCheckpoint(dict(use_mass=use_mass, obs_mode=a.obs, **kw), best_path, a.val_every)
        callbacks = CallbackList([cb, best_cb])
    model.learn(total_timesteps=a.timesteps, callback=callbacks)
    mins = (time.time() - t0) / 60
    if a.best:
        pd.DataFrame(best_cb.curve, columns=["timestep", "val_reward"]).to_csv(f"{out}/val_curve.csv", index=False)
        print("Validation reward by step:", " ".join(f"{t//1000}k:{v:.0f}" for t, v in best_cb.curve))
        model = (PPO if a.algo == "ppo" else SAC).load(best_path, device="cpu")
        print(f"Using best checkpoint (validation reward {best_cb.best:.1f})")
    model.save(f"{BASE}/drl_agent/models/{name}")
    print(f"Done: {cb.n} episodes, {a.timesteps} steps, {mins:.1f} min "
          f"({a.timesteps/(mins*60):.0f} steps/s)")

    agent, base = evaluate(model, use_mass, a.obs, **kw)
    gain = (agent["coverage_per_charge"] / base["coverage_per_charge"] - 1) * 100
    result = dict(name=name, algo=a.algo, use_mass=use_mass, hide_mass=a.hide_mass,
                  timesteps=a.timesteps,
                  settings=dict(obs=a.obs, best=a.best, lr_decay=a.lr_decay, **kw),
                  episodes=cb.n, minutes=mins, agent=agent, lawnmower=base,
                  gain_over_lawnmower_pct=gain, eval_seeds=len(EVAL_SEEDS))
    json.dump(result, open(f"{out}/eval.json", "w"), indent=2)

    print("\nEVALUATION on 30 held-out patches")
    print(f"  Lawnmower : {base['coverage_per_charge']:.3f} ha/charge  "
          f"battery {base['battery_used']:.1f}%  collisions/mission {base['collisions']:.2f}")
    print(f"  Agent     : {agent['coverage_per_charge']:.3f} ha/charge  "
          f"battery {agent['battery_used']:.1f}%  crash rate {agent['crash_rate']*100:.0f}%")
    print(f"  Change vs lawnmower: {gain:+.1f}%   SULEKO real baseline: 0.506 ha")
    if use_mlflow:
        mlflow.log_metrics({"eval_agent_cpc": agent["coverage_per_charge"],
                            "eval_lawnmower_cpc": base["coverage_per_charge"],
                            "eval_gain_pct": gain})
        mlflow.log_artifact(f"{out}/eval.json")
        mlflow.end_run()


if __name__ == "__main__":
    main()