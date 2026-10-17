# train.py
# Component 3 - train PPO or SAC on the tea-spray environment, log to MLflow,
# then evaluate on held-out patches against the fixed lawnmower route.
#
# Examples (from ~/component3, venv active):
#   python3 drl_agent/train.py --algo ppo --timesteps 200000
#   python3 drl_agent/train.py --algo sac --timesteps 100000
#   python3 drl_agent/train.py --algo ppo --timesteps 200000 --no-mass   # ablation

import os, sys, json, time, argparse
import numpy as np
import pandas as pd

BASE = os.environ.get("C3_BASE", os.path.expanduser("~/component3"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tea_spray_env import TeaSprayEnv, LawnmowerPolicy, run_episode

from stable_baselines3 import PPO, SAC
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.callbacks import BaseCallback

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


def evaluate(model, use_mass):
    agent, base = [], []
    env_a = TeaSprayEnv(terminate_on_collision=True, use_mass=use_mass)
    env_b = TeaSprayEnv(terminate_on_collision=False, use_mass=use_mass)
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
    ap.add_argument("--no-mass", action="store_true", help="ablation: energy ignores m(t)")
    ap.add_argument("--name", default=None)
    a = ap.parse_args()

    use_mass = not a.no_mass
    name = a.name or f"{a.algo}{'_nomass' if a.no_mass else ''}_{a.timesteps//1000}k_s{a.seed}"
    out = f"{BASE}/drl_agent/runs/{name}"
    os.makedirs(out, exist_ok=True)
    os.makedirs(f"{BASE}/drl_agent/models", exist_ok=True)

    env = Monitor(TeaSprayEnv(seed=a.seed, use_mass=use_mass),
                  info_keywords=("coverage_per_charge", "area_ha", "battery_used", "collisions"))
    common = dict(seed=a.seed, device="cpu", verbose=0)
    if a.algo == "ppo":
        model = PPO("MlpPolicy", env, n_steps=2048, batch_size=256, learning_rate=3e-4,
                    gamma=0.995, gae_lambda=0.95, ent_coef=0.0, **common)
    else:
        model = SAC("MlpPolicy", env, learning_rate=3e-4, buffer_size=200_000,
                    learning_starts=5_000, batch_size=256, gamma=0.995, **common)

    use_mlflow = mlflow is not None
    if use_mlflow:
        mlflow.set_tracking_uri(f"sqlite:///{BASE}/mlflow.db")
        mlflow.set_experiment("component3-routing")
        mlflow.start_run(run_name=name)
        mlflow.log_params(dict(algo=a.algo, timesteps=a.timesteps, seed=a.seed,
                               use_mass=use_mass))
    cb = LogCallback(f"{out}/train_log.csv", use_mlflow)

    print(f"Training {name} ...")
    t0 = time.time()
    model.learn(total_timesteps=a.timesteps, callback=cb)
    mins = (time.time() - t0) / 60
    model.save(f"{BASE}/drl_agent/models/{name}")
    print(f"Done: {cb.n} episodes, {a.timesteps} steps, {mins:.1f} min "
          f"({a.timesteps/(mins*60):.0f} steps/s)")

    agent, base = evaluate(model, use_mass)
    gain = (agent["coverage_per_charge"] / base["coverage_per_charge"] - 1) * 100
    result = dict(name=name, algo=a.algo, use_mass=use_mass, timesteps=a.timesteps,
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