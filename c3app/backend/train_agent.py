"""Train the one-agent route planner (PPO or SAC) and evaluate it on held-out estates.

Terrain split (so the test is a NEW estate, not a new random patch of the same ground):
  training fields  : left 60 % of the elevation tile
  validation fields: right 40 % (used for tuning only)
  test fields      : right 40 %, different seeds, never used for any choice
"""
import os, sys, json, time, argparse
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import fields as F
import agent_env as A
from stable_baselines3 import PPO, SAC
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.monitor import Monitor

TILE = os.environ.get("C3_TILE") or None
TRAIN_COLS, EVAL_COLS = (0.0, 0.6), (0.6, 1.0)


def tile():
    if TILE: return np.load(TILE)
    return np.load(os.path.join(os.environ.get("C3_BASE", os.path.expanduser("~/component3")), "terrain", "elevation_srtm.npy"))


def make_fields(z, seed, n, cols, **kw):
    rng = np.random.default_rng(seed)
    return [F.random_field(z, rng, cols=cols, **kw) for _ in range(n)]


def evaluate(model, fields, hide_mass=False, deterministic=True):
    """mean saving (%) of the agent against the standard route, per field"""
    env = A.MissionEnv(fixed_fields=fields, hide_mass=hide_mass)
    out = []
    for i in range(len(fields)):
        o, _ = env.reset()
        done = False
        while not done:
            a, _ = model.predict(o, deterministic=deterministic)
            o, r, done, _, info = env.step(a)
        out.append(dict(saving=info.get("saving_pct", -300.0), contact=info.get("contact", 1), sorties=info.get("sorties", 0),
                        failed=bool(info.get("failed")), e=info.get("energy", np.nan), e_std=env.e_std))
    return out


def summarise(res):
    s = np.array([min(r["saving"], 50.0) if r["contact"] == 0 else -50.0 for r in res])
    return dict(mean=float(s.mean()), median=float(np.median(s)), wins=int((s > 0.5).sum()), losses=int((s < -0.5).sum()), n=len(s))


def build(algo, env, hp, seed):
    pk = dict(net_arch=dict(pi=[hp.get("width", 64)] * hp.get("depth", 2), vf=[hp.get("width", 64)] * hp.get("depth", 2))) if algo == "ppo" \
        else dict(net_arch=[hp.get("width", 64)] * hp.get("depth", 2))
    if algo == "ppo":
        return PPO("MlpPolicy", env, learning_rate=hp.get("lr", 3e-4), n_steps=hp.get("n_steps", 512), batch_size=hp.get("batch", 128),
                   gamma=hp.get("gamma", 1.0), ent_coef=hp.get("ent", 0.0), clip_range=hp.get("clip", 0.2), n_epochs=hp.get("epochs", 10),
                   gae_lambda=hp.get("lam", 0.95), policy_kwargs=pk, seed=seed, verbose=0, device="cpu")
    return SAC("MlpPolicy", env, learning_rate=hp.get("lr", 3e-4), batch_size=hp.get("batch", 128), gamma=hp.get("gamma", 0.99),
               buffer_size=100000, learning_starts=1000, train_freq=1, tau=hp.get("tau", 0.005), policy_kwargs=pk, seed=seed, verbose=0, device="cpu")


def train(algo, steps, seed, hp, hide_mass=False, n_train=300, log=None, z=None):
    z = tile() if z is None else z
    pool = make_fields(z, 1000 + seed, n_train, TRAIN_COLS)
    env = DummyVecEnv([lambda i=i: Monitor(A.MissionEnv(fixed_fields=pool[i::2], hide_mass=hide_mass, seed=seed + i)) for i in range(2)])
    m = build(algo, env, hp, seed)
    t = time.time()
    m.learn(total_timesteps=steps)
    if log: print(f"  trained {algo} {steps} steps in {time.time()-t:.0f}s", file=log, flush=True)
    return m


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--algo", default="ppo"); ap.add_argument("--steps", type=int, default=100000)
    ap.add_argument("--seed", type=int, default=0); ap.add_argument("--hp", default="{}")
    ap.add_argument("--hide-mass", action="store_true"); ap.add_argument("--name", default=None)
    ap.add_argument("--n-train", type=int, default=300); ap.add_argument("--n-test", type=int, default=60)
    a = ap.parse_args()
    z = tile()
    hp = json.loads(a.hp)
    m = train(a.algo, a.steps, a.seed, hp, a.hide_mass, a.n_train, sys.stdout, z)
    test = make_fields(z, 9000, a.n_test, EVAL_COLS)
    res = evaluate(m, test, a.hide_mass)
    print("TEST", summarise(res))
    name = a.name or f"{a.algo}_s{a.seed}"
    os.makedirs(os.path.join(HERE, "..", "agents"), exist_ok=True)
    m.save(os.path.join(HERE, "..", "agents", name))
    json.dump(dict(hp=hp, steps=a.steps, seed=a.seed, hide_mass=a.hide_mass, test=summarise(res), per_field=res),
              open(os.path.join(HERE, "..", "agents", name + ".json"), "w"), default=float)
