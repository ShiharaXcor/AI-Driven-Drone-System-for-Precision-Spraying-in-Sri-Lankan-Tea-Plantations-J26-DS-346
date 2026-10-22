"""Version 2 of the mission agent: it also decides the ORDER in which the strips of the field are sprayed.

New action (5th number):  strip order
    below -1/3        plain order (rows one after another, as in version 1)
    -1/3 .. +1/3      flat first: the flattest strips are sprayed while the tank is full, the steepest last
    above +1/3        steep first: the opposite (so the agent can also learn when NOT to use flat first)
New inputs (2 more, 20 in all): how uneven the slope is inside the field, and the share of steep ground.

Everything else is the same as version 1 (agent_env.py): same follower, same energy model, same reward.
The reward never mentions flat first. The agent only gains from it if the energy model says it saves battery."""
import math
import numpy as np
from gymnasium import spaces
import agent_env as A1
from agent_env import MissionEnv as _V1, NeedAction, GRID, MAX_SORTIES, SORTIE_PEN, sortie_cap, make_problem, run_standard, run_planner
from flatfirst import row_slopes, make_chunks, order_of

OBS_N, ACT_N = 20, 5
ORDER_NAMES = ("plain order", "flat first", "steep first")


def order_mode(a):
    return 0 if a < -1 / 3 else (1 if a <= 1 / 3 else 2)


def strip_order(P, fr, flip_rows, mode):
    """row order for one of the three modes. Strips are about a third of a tank of rows, as in flatfirst.py"""
    nrows = len(fr.rows())
    base = list(range(nrows))[::-1] if flip_rows else list(range(nrows))
    if mode == 0 or nrows < 3:
        return None
    row_len = np.mean([sum(b - a for a, b in ivs) for _, ivs in fr.rows()])
    rows_per_tank = max(1.0, P.tank / max(P.l_per_m * row_len, 1e-6))
    per = int(max(2, round(rows_per_tank / 3)))
    chunks = [[base[j] for j in c] for c in make_chunks(nrows, per)]
    if len(chunks) < 2:
        return None
    sl = row_slopes(P, fr)
    cs = np.array([sl[c].mean() for c in chunks])
    perm = list(np.argsort(cs if mode == 1 else -cs, kind="stable"))
    return order_of(chunks, perm, [False] * len(chunks))


class MissionEnv(_V1):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.observation_space = spaces.Box(0.0, 1.0, (OBS_N,), np.float32)
        self.action_space = spaces.Box(-1.0, 1.0, (ACT_N,), np.float32)

    def _static(self):
        super()._static()
        P = self.P
        gy, gx = np.gradient(P.z, GRID)
        sl = np.degrees(np.arctan(np.hypot(gx, gy)))
        from fields import in_poly
        poly = P.poly
        lo, hi = poly.min(0), poly.max(0)
        ii, jj = np.meshgrid((np.arange(P.z.shape[0]) + .5) * GRID, (np.arange(P.z.shape[1]) + .5) * GRID, indexing="ij")
        m = (ii >= lo[0]) & (ii <= hi[0]) & (jj >= lo[1]) & (jj <= hi[1])
        idx = np.where(m.ravel())[0][::4]
        ins = np.array([in_poly((ii.ravel()[k], jj.ravel()[k]), poly) for k in idx]) if len(idx) else np.array([], bool)
        v = sl.ravel()[idx[ins]] if ins.any() else sl.ravel()[idx]
        self.static = np.concatenate([self.static, np.array([min(float(v.std()) / 15.0, 1.0), float((v > 12).mean())], np.float32)])

    def step(self, action):
        a = np.asarray(action, float).ravel()
        if self.design is not None:           # later steps (refills): same as version 1
            return super().step(a[:4])
        self.steps += 1
        try:
            self.a0 = float(np.clip(a[0], -1, 1))
            th = round((self.th_std + 90.0 * self.a0) % 180.0)
            self.design = (th, bool(a[1] > 0), bool(a[2] > 0))
            self.mode = order_mode(float(a[4]))
            fr_cache = self.field.setdefault("_frames", {}) if self.field.get("_P") is self.P else {}
            self.frame = fr_cache.get(th) or fr_cache.setdefault(th, A1.Frame(self.P, float(th)))
            okey = ("order", th, self.design[1], self.mode)
            if okey not in fr_cache:
                fr_cache[okey] = strip_order(self.P, self.frame, self.design[1], self.mode)
            self.order = fr_cache[okey]
            self.path = self.frame.build(self.design[1], self.design[2], True, order=self.order)
            try:
                self._run()
            except NeedAction:
                pass
            zs = self.frame.elev(self.path[0], self.path[1])
            self.rem_slope = float(min(np.degrees(np.arctan(np.abs(np.diff(zs)).mean() / 1.8)) / 45.0, 1.0))
            self.fills.append(self._litres(a[3], self.ctx["need"]))
            S = self._run()
        except NeedAction:
            return self._obs(False), 0.0, False, False, {}
        except RuntimeError:
            return self._obs(False), -3.0, True, False, {"failed": True}
        return self._finish(S)

    def _finish(self, S):
        e = sum(S["sortie_e"].values()) + 1000.0 * S["contact"]
        e_clean = sum(S["sortie_e"].values())
        r = float(np.clip((self.e_std - e_clean) / self.e_std * 10.0, -3.0, 3.0))
        if S["contact"] > 0:
            r -= 1.0 + 0.25 * min(int(S["contact"]), 8)
        r -= SORTIE_PEN * max(0, int(S["sortie"]) - self.sortie_cap)
        r = float(max(r, -5.0))
        info = dict(energy=e, e_std=self.e_std, saving_pct=(1 - e / self.e_std) * 100, sorties=S["sortie"], contact=S["contact"],
                    design=self.design, fills=list(self.fills), order_mode=getattr(self, "mode", 0))
        self.S = S
        return self._obs(False), r, True, False, info
