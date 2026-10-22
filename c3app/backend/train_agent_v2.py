"""Train / test the version-2 agent (it also chooses the strip order).  Same options as train_agent.py.
Example (from c3app/backend):  python3 train_agent_v2.py --steps 60000 --seed 0 --name mission_ppo_v2_s0
Energy scenario (refit model):  C3_SCENARIO=a10 python3 train_agent_v2.py ...   (see energy_scenario.py)"""
import sys, os, json, argparse, collections
import numpy as np
import agent_env_v2 as V
import train_agent as T
T.A = V                                   # train_agent builds MissionEnv from module A: use version 2

def order_use(model, fields):
    env = V.MissionEnv(fixed_fields=fields)
    cnt = collections.Counter()
    for _ in fields:
        o, _i = env.reset(); done = False
        while not done:
            a, _ = model.predict(o, deterministic=True)
            o, r, done, _t, info = env.step(a)
        cnt[V.ORDER_NAMES[getattr(env, "mode", 0)]] += 1
    return dict(cnt)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--algo", default="ppo"); ap.add_argument("--steps", type=int, default=100000)
    ap.add_argument("--seed", type=int, default=0); ap.add_argument("--hp", default="{}")
    ap.add_argument("--hide-mass", action="store_true"); ap.add_argument("--name", default=None)
    ap.add_argument("--n-train", type=int, default=300); ap.add_argument("--n-test", type=int, default=60)
    a = ap.parse_args()
    z = T.tile(); hp = json.loads(a.hp)
    m = T.train(a.algo, a.steps, a.seed, hp, a.hide_mass, a.n_train, sys.stdout, z)
    test = T.make_fields(z, 9000, a.n_test, T.EVAL_COLS)
    res = T.evaluate(m, test, a.hide_mass)
    use = order_use(m, T.make_fields(z, 9000, a.n_test, T.EVAL_COLS))
    print("TEST", T.summarise(res)); print("strip order chosen on the test fields:", use)
    name = a.name or f"mission_ppo_ord_s{a.seed}"
    d = os.path.join(T.HERE, "..", "agents"); os.makedirs(d, exist_ok=True)
    m.save(os.path.join(d, name))
    json.dump(dict(hp=hp, steps=a.steps, seed=a.seed, hide_mass=a.hide_mass, version=2, test=T.summarise(res), order_use=use, per_field=res),
              open(os.path.join(d, name + ".json"), "w"), default=float)
