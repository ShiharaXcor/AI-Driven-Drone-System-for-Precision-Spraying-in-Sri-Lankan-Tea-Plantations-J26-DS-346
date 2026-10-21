"""Hyperparameter search (Optuna) for the mission agent.

The objective is the mean saving against the standard route on VALIDATION fields only
(terrain from the right 40 % of the tile, seeds 7000+). The test fields (seed 9000) are never touched here.
The study is stored in SQLite so you can stop it and resume it.

  python3 c3app/backend/tune_agent.py --algo ppo --trials 20 --steps 30000
"""
import os, sys, json, time, argparse
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import optuna
import train_agent as T


def suggest(trial, algo):
    if algo == "ppo":
        return dict(lr=trial.suggest_float("lr", 1e-4, 3e-3, log=True), n_steps=trial.suggest_categorical("n_steps", [256, 512, 1024]),
                    batch=trial.suggest_categorical("batch", [64, 128, 256]), ent=trial.suggest_float("ent", 1e-4, 3e-2, log=True),
                    gamma=trial.suggest_categorical("gamma", [0.98, 0.99, 1.0]), clip=trial.suggest_categorical("clip", [0.1, 0.2, 0.3]),
                    lam=trial.suggest_categorical("lam", [0.9, 0.95, 0.98]), width=trial.suggest_categorical("width", [64, 128]),
                    depth=trial.suggest_categorical("depth", [2, 3]))
    return dict(lr=trial.suggest_float("lr", 1e-4, 1e-3, log=True), batch=trial.suggest_categorical("batch", [64, 128, 256]),
                gamma=trial.suggest_categorical("gamma", [0.95, 0.98, 0.99]), tau=trial.suggest_categorical("tau", [0.005, 0.01, 0.02]),
                width=trial.suggest_categorical("width", [64, 128]), depth=trial.suggest_categorical("depth", [2, 3]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--algo", default="ppo"); ap.add_argument("--trials", type=int, default=20)
    ap.add_argument("--steps", type=int, default=30000); ap.add_argument("--n-val", type=int, default=24)
    ap.add_argument("--n-train", type=int, default=150)
    a = ap.parse_args()
    z = T.tile()
    val = T.make_fields(z, 7000, a.n_val, T.EVAL_COLS)
    os.makedirs(os.path.join(HERE, "..", "agents"), exist_ok=True)
    db = f"sqlite:///{os.path.abspath(os.path.join(HERE, '..', 'agents', f'optuna_{a.algo}.db'))}"
    study = optuna.create_study(study_name=f"{a.algo}_mission", storage=db, load_if_exists=True, direction="maximize",
                                sampler=optuna.samplers.TPESampler(seed=0))

    def objective(trial):
        hp = suggest(trial, a.algo)
        t = time.time()
        m = T.train(a.algo, a.steps, seed=trial.number, hp=hp, n_train=a.n_train, z=z)
        s = T.summarise(T.evaluate(m, val))
        print(f"trial {trial.number}: validation saving {s['mean']:+.2f}% (median {s['median']:+.2f}, wins {s['wins']}/{s['n']}) "
              f"{time.time() - t:.0f}s  {hp}", flush=True)
        return s["mean"]

    study.optimize(objective, n_trials=a.trials)
    best = dict(algo=a.algo, value=study.best_value, hp=study.best_params, steps=a.steps)
    json.dump(best, open(os.path.join(HERE, "..", "agents", f"best_hp_{a.algo}.json"), "w"), indent=1)
    print("BEST", best)


if __name__ == "__main__":
    main()
