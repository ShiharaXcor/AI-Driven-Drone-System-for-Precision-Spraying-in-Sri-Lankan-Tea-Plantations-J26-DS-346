"""Use a trained mission agent to plan the route for a field (used by the web app).

The agent looks at the field (shape, slope, trees, tank, refill point) and decides:
  row direction, sweep direction, and the liquid to load at every refill.
The rows themselves are flown by the same follower and scored with the same energy model as every other route.
"""
import os, glob, json, threading
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
AGENTS = os.environ.get("C3_AGENTS") or os.path.abspath(os.path.join(HERE, "..", "agents"))
_models, _lock = {}, threading.Lock()


def list_agents():
    out = []
    for p in sorted(glob.glob(os.path.join(AGENTS, "*.zip"))):
        name = os.path.basename(p)[:-4]
        if name.startswith(("optuna", "eval_", "smoke")):
            continue
        info = {}
        jp = os.path.join(AGENTS, name + ".json")
        if os.path.exists(jp):
            try:
                j = json.load(open(jp))
                info = dict(test=j.get("test"), steps=j.get("steps"), hide_mass=j.get("hide_mass"))
            except Exception:
                pass
        out.append(dict(name=name, **info))
    return out


def _load(name):
    with _lock:
        if name not in _models:
            from stable_baselines3 import PPO, SAC
            p = os.path.join(AGENTS, name + ".zip")
            if not os.path.exists(p):
                raise RuntimeError(f"agent '{name}' not found in {AGENTS}")
            _models[name] = (SAC if name.startswith("sac") else PPO).load(p, device="cpu")
        return _models[name]


def decide(name, P):
    """run the agent on the planning problem P; return its decisions"""
    import agent_env as A
    model = _load(name)
    f = dict(z=P.z, poly=P.poly, trees=[dict(x=float(a), y=float(b), r=float(r)) for (a, b), r in zip(P.trees, P.rad)],
             depot=np.asarray(P.depot, float), tank_l=float(P.tank), params=dict(P.par))
    env = A.plan_with_agent(model, f, hide_mass=("blind" in name))
    if env is None:
        raise RuntimeError("the agent could not finish a plan for this field")
    th, fr_, fd = env.design
    return dict(theta=float(th), flip_rows=bool(fr_), flip_dir=bool(fd), fills=[float(x) for x in env.fills])
