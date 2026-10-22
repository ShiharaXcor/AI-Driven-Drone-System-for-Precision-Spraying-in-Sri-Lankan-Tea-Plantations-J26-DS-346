"""One trained agent plans the whole mission.

The agent decides, from the field it is given:
  step 1 : row direction, sweep direction (2 flips) and how much liquid to load for sortie 1
  step k : how much liquid to load at every later refill
A fixed follower then flies the rows (tree arcs, battery reserve, return flights) with the same
energy model the baselines use, so every route is scored the same way.

The environment is plain Gymnasium, so PPO or SAC from Stable-Baselines3 train on it directly.
"""
import os, sys, math
import numpy as np
import gymnasium as gym
from gymnasium import spaces

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import engine as EN
from engine import Problem, Frame, Flight, longest_edge_deg, poly_area, poly_centroid, DEFAULTS, GRID

OBS_N, ACT_N, MAX_SORTIES = 18, 4, 8
SORTIE_PEN = 0.3


def sortie_cap(s_std):
    """a plan may use at most twice the sorties of the standard route, plus two"""
    return 2 * int(s_std) + 2

MODEL = None


def get_model():
    global MODEL
    if MODEL is None:
        import energy_scenario as ES
        MODEL = ES.apply(EN.E.load_model())
    return MODEL


class NeedAction(Exception):
    pass


def make_problem(f, spray_kmh=None, params=None):
    par = dict(DEFAULTS)
    par["tank_l"] = float(f["tank_l"])
    if spray_kmh:
        par["spray_kmh"] = float(spray_kmh)
    par.update(f.get("params") or {})
    par.update(params or {})
    par["tank_l"] = float(f["tank_l"]) if "tank_l" in f else par["tank_l"]
    return Problem(f["z"], f["poly"], f["trees"], f["depot"], par, get_model())


def run_standard(P):
    """the fair baseline: rows along the longest edge, tree arcs, full tanks (last one trimmed); best of 4 start/sweep choices"""
    th = longest_edge_deg(P.poly)
    fr = Frame(P, th)
    fl = Flight(fr)
    best = None
    for a, b in ((False, False), (False, True), (True, False), (True, True)):
        try:
            S = fl.run(fr.build(a, b, True), "trim")
        except RuntimeError:
            continue
        e = sum(S["sortie_e"].values()) + 1000.0 * S["contact"]
        if best is None or e < best[0]:
            best = (e, S)
    return best[0], best[1], th


def run_planner(P, coarse=False):
    """the search planner (benchmark): many row directions x 4 sweeps, load-levelled refills"""
    th0 = longest_edge_deg(P.poly)
    thetas = sorted(set([float(t) for t in range(0, 180, 30 if coarse else 15)] + [th0, (th0 + 90) % 180]))
    best = None
    for th in thetas:
        fr = Frame(P, th)
        fl = Flight(fr)
        for a, b in ((False, False), (False, True), (True, False), (True, True)):
            try:
                S = fl.run(fr.build(a, b, True), True)
            except RuntimeError:
                continue
            e = sum(S["sortie_e"].values()) + 1000.0 * S["contact"]
            if best is None or e < best[0]:
                best = (e, S, th, a, b)
    return best


class MissionEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, field_fn=None, seed=0, fixed_fields=None, hide_mass=False):
        super().__init__()
        self.field_fn = field_fn
        self.fixed = fixed_fields           # optional list of ready fields (cycled) - used for evaluation
        self._i = 0
        self.rng = np.random.default_rng(seed)
        self.hide_mass = hide_mass          # ablation: the agent does not see tank size / liquid still needed
        self.observation_space = spaces.Box(0.0, 1.0, (OBS_N,), np.float32)
        self.action_space = spaces.Box(-1.0, 1.0, (ACT_N,), np.float32)
        self.P = None

    # ------------------------------------------------------------------ features
    def _static(self):
        P = self.P
        poly = P.poly
        c = poly_centroid(poly)
        th0 = math.radians(self.th_std)
        # terrain inside the polygon
        gy, gx = np.gradient(P.z, GRID)
        sl = np.degrees(np.arctan(np.hypot(gx, gy)))
        ii, jj = np.meshgrid((np.arange(P.z.shape[0]) + .5) * GRID, (np.arange(P.z.shape[1]) + .5) * GRID, indexing="ij")
        from fields import in_poly
        lo, hi = poly.min(0), poly.max(0)
        m = (ii >= lo[0]) & (ii <= hi[0]) & (jj >= lo[1]) & (jj <= hi[1])
        pts = np.stack([ii[m], jj[m]], 1)
        ins = np.array([in_poly(p, poly) for p in pts[::4]])
        sel = np.where(m.ravel())[0][::4][ins] if ins.any() else np.where(m.ravel())[0][::4]
        zf, gxf, gyf, slf = P.z.ravel()[sel], gx.ravel()[sel], gy.ravel()[sel], sl.ravel()[sel]
        asp = math.atan2(gyf.mean(), gxf.mean())                 # uphill direction
        # elongation from the principal axes of the polygon
        q = poly - c
        ev = np.linalg.eigvalsh(q.T @ q / len(q))
        elong = math.sqrt(max(ev[0], 1e-9) / max(ev[1], 1e-9))
        d = P.depot - c
        dang = math.atan2(d[1], d[0])
        need_l = P.l_per_m * (poly_area(poly) / P.spacing) * 1.1
        self.need_total = need_l
        self.static = np.array([
            min(poly_area(poly) / 1e4 / 3.0, 1), elong, min(P.tank / 40.0, 1), min(need_l / P.tank / 8.0, 1),
            min(len(P.trees) / 20.0, 1), min(slf.mean() / 45.0, 1), (math.cos(asp - th0) + 1) / 2, (math.sin(asp - th0) + 1) / 2,
            min((zf.max() - zf.min()) / 150.0, 1), min(float(np.hypot(*d)) / 200.0, 1)], np.float32)
        self.depot_dz = float(np.clip((P.home_alt - zf.mean()) / 100.0, -1, 1) * .5 + .5)
        self.dang = ((math.cos(dang - th0) + 1) / 2)
        if self.hide_mass:
            self.static[2] = 0.5
            self.static[3] = 0.5

    def _obs(self, first):
        P = self.P
        s = self.static
        if first:
            dyn = [0.0, min(self.need_total / P.tank / 8.0, 1) if not self.hide_mass else .5, 0.0, 0.0, 0.0, 0.5]
        else:
            need, frac, k = self.ctx["need"], self.ctx["frac"], self.ctx["k"]
            dyn = [1.0, min(need / P.tank / 8.0, 1) if not self.hide_mass else .5, frac, min(k / 8.0, 1), self.rem_slope, (self.a0 + 1) / 2]
        o = np.concatenate([s, [self.depot_dz, self.dang], np.array(dyn, np.float32)])   # 10 + 2 + 6 = 18
        return np.clip(o, 0, 1).astype(np.float32)

    # ------------------------------------------------------------------ episode
    def reset(self, seed=None, options=None):
        if seed is not None:
            self.rng = np.random.default_rng(seed)
        if options and "field" in options:
            f = options["field"]
        elif self.fixed is not None:
            f = self.fixed[self._i % len(self.fixed)]
            self._i += 1
        else:
            f = self.field_fn(self.rng)
        self.field = f
        sk = (options or {}).get("spray_kmh")
        if sk is None and "_P" in f:
            self.P = f["_P"]                      # the same field is revisited many times: keep its problem and path caches
        else:
            self.P = make_problem(f, sk)
            if sk is None:
                f["_P"] = self.P
                f["_frames"] = {}
        self.th_std = longest_edge_deg(self.P.poly)
        self.e_std = f.get("e_std")
        if self.e_std is None or "s_std" not in f:
            self.e_std, S_std, _ = run_standard(self.P)
            f["e_std"] = self.e_std
            f["s_std"] = int(S_std["sortie"])
        self.sortie_cap = sortie_cap(f["s_std"])
        self._static()
        self.fills, self.ctx, self.path = [], {}, None
        self.design = None
        self.rem_slope = 0.0
        self.steps = 0
        return self._obs(True), {}

    def _litres(self, a_fill, need):
        P = self.P
        frac = 0.2 + 0.8 * (float(np.clip(a_fill, -1, 1)) + 1) / 2
        return float(min(frac * P.tank, need + 0.2))

    def _run(self):
        """replay the mission with the loads chosen so far; stop (NeedAction) at the next refill"""
        k = [0]
        ctx = self.ctx

        def cb(info):
            j = k[0]
            k[0] += 1
            if j < len(self.fills):
                return self.fills[j]
            ctx.update(need=info["need"], frac=float(info["idx"]) / max(len(info["cs"]) - 1, 1), k=j)
            raise NeedAction()
        th, fr_, fd = self.design
        fr = self.frame
        fl = Flight(fr)
        return fl.run(self.path, cb)

    def step(self, action):
        a = np.asarray(action, float).ravel()
        self.steps += 1
        first = self.design is None
        try:
            if first:
                self.a0 = float(np.clip(a[0], -1, 1))
                th = (self.th_std + 90.0 * self.a0) % 180.0
                th = round(th)                       # whole degrees
                self.design = (th, bool(a[1] > 0), bool(a[2] > 0))
                fr_cache = self.field.setdefault("_frames", {}) if self.field.get("_P") is self.P else {}
                self.frame = fr_cache.get(th) or fr_cache.setdefault(th, Frame(self.P, float(th)))
                self.path = self.frame.build(self.design[1], self.design[2], True)
                try:
                    self._run()
                except NeedAction:
                    pass
                zs = self.frame.elev(self.path[0], self.path[1])
                dz = np.diff(zs)
                self.rem_slope = float(min(np.degrees(np.arctan(np.abs(dz).mean() / 1.8)) / 45.0, 1.0))
            self.fills.append(self._litres(a[3], self.ctx["need"]))
            S = self._run()
        except NeedAction:
            return self._obs(False), 0.0, False, False, {}
        except RuntimeError:
            return self._obs(False), -3.0, True, False, {"failed": True}
        e = sum(S["sortie_e"].values()) + 1000.0 * S["contact"]
        e_clean = sum(S["sortie_e"].values())
        r = float(np.clip((self.e_std - e_clean) / self.e_std * 10.0, -3.0, 3.0))
        if S["contact"] > 0:                       # graded: one touch costs 1.0, a bad route up to 3.0
            r -= 1.0 + 0.25 * min(int(S["contact"]), 8)
        r -= SORTIE_PEN * max(0, int(S["sortie"]) - self.sortie_cap)   # no endless tiny sorties
        r = float(max(r, -5.0))
        info = dict(energy=e, e_std=self.e_std, saving_pct=(1 - e / self.e_std) * 100, sorties=S["sortie"],
                    contact=S["contact"], design=self.design, fills=list(self.fills))
        self.S = S
        return self._obs(False), r, True, False, info


def plan_with_agent(model, field, hide_mass=False, tries=8, seed=0):
    """Run the agent on a field. The first try is the agent's own best guess (deterministic).
    If that route touches a tree or uses too many sorties, try a few more samples of the same agent and keep the best safe one.
    Returns the finished env (env.design, env.fills, env.S) or None."""
    best = None
    for k in range(tries + 1):
        env = MissionEnv(fixed_fields=[field], hide_mass=hide_mass)
        env.rng = np.random.default_rng(seed + k)
        o, _ = env.reset()
        done, info = False, {}
        for _ in range(MAX_SORTIES * 6):
            a, _ = model.predict(o, deterministic=(k == 0))
            o, r, done, _, info = env.step(a)
            if done:
                break
        if not done or info.get("failed") or not hasattr(env, "S"):
            continue
        bad = env.S["contact"] > 0 or env.S["sortie"] > env.sortie_cap
        key = (bad, env.S["contact"], sum(env.S["sortie_e"].values()))
        if best is None or key < best[0]:
            best = (key, env)
        if not bad and k == 0:
            break
        if k >= 1 and best is not None and not best[0][0] and k >= 3:
            break
    return None if best is None else best[1]
