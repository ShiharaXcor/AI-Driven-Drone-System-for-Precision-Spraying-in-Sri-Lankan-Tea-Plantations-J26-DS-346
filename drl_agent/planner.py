# planner.py
# Component 3 - energy-aware route PLANNER (rule-based + search, no learning).
#
# Run (from ~/component3, venv active):
#   python3 drl_agent/planner.py --validate                  # check the scorer against the simulator first
#   python3 drl_agent/planner.py --seed 7000                 # plan one 100 m x 100 m field
#   python3 drl_agent/planner.py --seed 7000 --field 10 10 190 190 --block 40 --iters 300
#
# What it does
#   1. Takes a terrain patch (real SRTM heights), tree positions, a field rectangle and the base point.
#   2. Splits the field into blocks. Inside a block the drone flies a serpentine sweep (same swath spacing
#      for every route, trees avoided by a detour).  Coverage is guaranteed by the sweep and then CHECKED
#      on a 2 m grid.
#   3. Builds several block orders (the fixed routes and the "rule" routes) and one SEARCHED order, and
#      scores every one with the SAME calibrated energy model the simulator uses, including the tank mass
#      that falls as liquid is sprayed, refill trips to the base and the battery reserve.
#   4. Prints the table and writes planner_output/plan_<seed>.json for the 3D viewer.
#
# Rule being tested: "spray the flat blocks while the tank is heavy, the steep blocks later when it is light".
# The planner does not assume the rule helps - the table shows what each order really costs.

import os, sys, json, argparse, time
import numpy as np
from scipy.ndimage import map_coordinates
from scipy.spatial import cKDTree

BASE = os.environ.get("C3_BASE", os.path.expanduser("~/component3"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tea_spray_env as E
from tea_spray_env import TeaSprayEnv

SPRAY_V = E.V_MAX          # m/s, spraying speed (same as simulator)
TRANSIT_V = E.TRANSIT_V    # m/s, flying without spraying
H_AGL = 3.0                # height above ground (simulator default)


class Planner:
    def __init__(self, z, trees, rad, model, field, home=(5.0, 5.0), block=25.0, spacing=5.5,
                 reserve=15.0, use_mass=True, margin=3.0):
        self.z, self.model = z, model
        self.trees, self.rad = np.asarray(trees, float).reshape(-1, 2), np.asarray(rad, float)
        self.field, self.home = tuple(field), np.array(home, float)
        self.spacing, self.reserve, self.use_mass, self.margin = spacing, reserve, use_mass, margin
        gx, gy = np.gradient(z, E.TERRAIN_DX)
        self.slope = np.degrees(np.arctan(np.hypot(gx, gy)))
        self.blocks = self._make_blocks(block)
        self.block_size = block
        self._cache = {}
        self.home_alt = float(self.elev(self.home[0], self.home[1])[0])

    # ---------------------------------------------------------------- terrain
    def _interp(self, g, x, y):
        x, y = np.atleast_1d(np.asarray(x, float)), np.atleast_1d(np.asarray(y, float))
        shp = np.broadcast(x, y).shape
        r = map_coordinates(g, [np.broadcast_to(x, shp).ravel() / E.TERRAIN_DX - 0.5,
                                np.broadcast_to(y, shp).ravel() / E.TERRAIN_DX - 0.5], order=1, mode="nearest")
        return r.reshape(shp)

    def elev(self, x, y):
        return self._interp(self.z, x, y)

    def slope_at(self, x, y):
        return self._interp(self.slope, x, y)

    def _edges(self, lo, hi, size):
        """block edges that sit on whole numbers of sweep rows, so every route uses the same row spacing"""
        n = max(1, int(np.ceil((hi - lo) / self.spacing - 1e-6)))
        sp = (hi - lo) / n
        k = max(1, int(round(size / sp)))
        e = [lo + sp * k * i for i in range(n // k + 1) if lo + sp * k * i < hi - 1e-6]
        return np.array(e + [hi])

    def _make_blocks(self, size, layout="grid"):
        x0, y0, x1, y1 = self.field
        if layout == "grid":
            xe, ye = self._edges(x0, x1, size), self._edges(y0, y1, size)
        elif layout == "bands_y":          # full-length rows along x, bands stacked in y
            xe, ye = np.array([x0, x1]), self._edges(y0, y1, size)
        else:                              # bands_x: rows along y, bands stacked in x
            xe, ye = self._edges(x0, x1, size), np.array([y0, y1])
        nx, ny = len(xe) - 1, len(ye) - 1
        out = []
        for i in range(nx):
            for j in range(ny):
                r = (xe[i], ye[j], xe[i + 1], ye[j + 1])
                gx, gy = np.meshgrid(np.linspace(r[0], r[2], 9), np.linspace(r[1], r[3], 9), indexing="ij")
                out.append(dict(id=len(out), rect=r, centre=((r[0] + r[2]) / 2, (r[1] + r[3]) / 2),
                                slope=float(self.slope_at(gx, gy).mean())))
        return out

    # ---------------------------------------------------------------- trees
    def detour(self, a, b, depth=0):
        """polyline from a to b that goes round any tree buffer on the way"""
        a, b = np.asarray(a, float), np.asarray(b, float)
        d = b - a
        L = float(np.hypot(*d))
        if L < 1e-6 or depth > 6 or len(self.trees) == 0:
            return [a, b]
        u = d / L
        best = None
        for c, r in zip(self.trees, self.rad):
            R = r + self.margin
            for e in (a, b):                               # an end point already inside the buffer
                de = float(np.hypot(*(e - c)))
                if de < R:
                    R = min(R, max(r + 1.6, de - 0.05))
            t = float(np.dot(c - a, u))
            if t < -R or t > L + R:
                continue
            q = a + u * np.clip(t, 0, L)
            if np.hypot(*(c - q)) < R * 0.999 and (best is None or t < best[0]):
                best = (t, c, R)
        if best is None:
            return [a, b]
        _, c, R = best
        n = np.array([-u[1], u[0]])
        nn = n if np.dot(c - a, n) <= 0 else -n            # pass on the side away from the centre
        Rp = 1.15 * R
        wp = [c + Rp * (-u * np.cos(np.radians(f)) + nn * np.sin(np.radians(f))) for f in (35, 90, 145)]
        chain = [a] + wp + [b]
        out = [a]
        for p, q in zip(chain[:-1], chain[1:]):
            out += self.detour(p, q, depth + 1)[1:]
        return out

    # ---------------------------------------------------------------- geometry of sweeps
    @staticmethod
    def dense(path, step):
        P = np.asarray(path, float)
        seg = np.hypot(*np.diff(P, axis=0).T)
        c = np.r_[0.0, np.cumsum(seg)]
        if c[-1] < 1e-9:
            return P[:1, 0], P[:1, 1]
        n = max(1, int(np.ceil(c[-1] / step)))
        s = np.linspace(0, c[-1], n + 1)
        return np.interp(s, c, P[:, 0]), np.interp(s, c, P[:, 1])

    def row_path(self, axis, p, q):
        """one straight sweep row p -> q; every tree buffer on it is replaced by an arc on the row's own side"""
        p, q = np.array(p, float), np.array(q, float)
        a, b = (p[0], q[0]) if axis == 0 else (p[1], q[1])           # along-row coordinate
        o = p[1] if axis == 0 else p[0]                              # across-row coordinate
        sgn = 1.0 if b >= a else -1.0
        lo, hi = min(a, b), max(a, b)
        hits = []
        for c, r in zip(self.trees, self.rad):
            cx, cy = (c[0], c[1]) if axis == 0 else (c[1], c[0])     # (along, across)
            R = r + self.margin
            dy = o - cy
            if abs(dy) >= R * 0.98:
                continue
            h = np.sqrt(max(R * R - dy * dy, 0.0))
            if cx + h < lo or cx - h > hi:
                continue
            hits.append((cx, cy, R, dy, h))
        hits.sort(key=lambda t: t[0] * sgn)
        pts, last = [(a, o)], -1e9
        for cx, cy, R, dy, h in hits:
            e1, e2 = (cx - h, cx + h) if sgn > 0 else (cx + h, cx - h)      # entry, exit along travel
            if e1 * sgn < last * sgn + 1e-9 and last != -1e9:
                continue                                                   # overlaps the previous buffer: skip
            if (e1 - a) * sgn < 0 or (b - e2) * sgn < 0:                   # row end falls inside the buffer: clip it
                e1 = a if (e1 - a) * sgn < 0 else e1
                e2 = b if (b - e2) * sgn < 0 else e2
            th1, th2 = np.arctan2(dy, e1 - cx), np.arctan2(dy, e2 - cx)
            if (e1 - a) * sgn >= 0:
                pts.append((e1, o))
            side = 1.0 if dy >= 0 else -1.0
            n_arc = max(2, int(abs(th2 - th1) / np.radians(15)))
            for t in np.linspace(th1, th2, n_arc + 1)[1:-1]:
                pts.append((cx + R * np.cos(t), cy + R * np.sin(t)))
            pts.append((e2, o))
            last = e2
        pts.append((b, o))
        return [np.array(u if axis == 0 else (u[1], u[0]), float) for u in pts]

    def variants(self, rect, axis, spacing=None, use_detour=True):
        """4 serpentine sweeps of a rectangle along axis 0 (x) or 1 (y): which end/row to start from"""
        key = (rect, axis, spacing, use_detour)
        if key in self._cache:
            return self._cache[key]
        sp0 = spacing or self.spacing
        x0, y0, x1, y1 = rect
        Ln, Wd = (x1 - x0, y1 - y0) if axis == 0 else (y1 - y0, x1 - x0)
        n = max(1, int(np.ceil(Wd / sp0 - 1e-6)))
        sp = Wd / n
        offs = [(k + 0.5) * sp for k in range(n)]
        out = []
        for flip_rows in (False, True):
            for flip_dir in (False, True):
                rows = offs[::-1] if flip_rows else offs
                pts = []
                for i, o in enumerate(rows):
                    fwd = (i % 2 == 0) != flip_dir
                    a, b = (0.0, Ln) if fwd else (Ln, 0.0)
                    pts += [(x0 + a, y0 + o), (x0 + b, y0 + o)] if axis == 0 else [(x0 + o, y0 + a), (x0 + o, y0 + b)]
                path = [np.array(pts[0], float)]
                for k in range(0, len(pts), 2):                      # rows: pts[k] -> pts[k+1]
                    row = self.row_path(axis, pts[k], pts[k + 1]) if use_detour else [np.array(pts[k], float), np.array(pts[k + 1], float)]
                    path += row[1:]
                    if k + 2 < len(pts):                             # short shift to the next row
                        nxt = np.array(pts[k + 2], float)
                        path += [nxt]                                  # shifts are 5 m: kept straight (clearance is reported)
                x, y = self.dense(path, SPRAY_V)
                out.append(dict(start=(x[0], y[0]), end=(x[-1], y[-1]), x=x, y=y))
        self._cache[key] = out
        return out

    def piece(self, rect, axis, frm, spacing=None, use_detour=True):
        v = self.variants(rect, axis, spacing, use_detour)
        best = min(v, key=lambda o: np.hypot(o["start"][0] - frm[0], o["start"][1] - frm[1]))
        return best["x"], best["y"], best["end"]

    # ---------------------------------------------------------------- energy
    def _power(self, m, ang_deg, v):
        mdl = self.model
        s = np.radians(np.clip(ang_deg, 0, 60))
        p = mdl.hover_power(m) + np.maximum(0.0, m * mdl.g * v * np.sin(s) * mdl.k_climb) + 0.5 * mdl.k_drag * v ** 2
        return p * mdl.level_scale / 3600.0 / mdl.battery_wh * 100.0      # battery % per second

    def costs(self, x, y, v, liq0, spraying):
        """battery % of every 1-step along the dense path, liquid at every point"""
        d = np.hypot(np.diff(x), np.diff(y))
        dt = np.maximum(d, 1e-9) / v
        alt = self.elev(x, y) + H_AGL
        rr = np.maximum(np.diff(alt) / dt, 0.0)
        ang = np.minimum(np.degrees(np.arctan2(rr, max(v, 0.2))), 60.0)
        liq = np.maximum(liq0 - (E.L_PER_M * np.r_[0.0, np.cumsum(d)] if spraying else np.zeros(len(x))), 0.0)
        m = self.model.mass_empty_kg + (liq[:-1] if self.use_mass else E.LIQUID_L / 2)
        return self._power(m, ang, v) * dt, liq

    def ret_cost(self, x, y, liq):
        """quick estimate of the battery % needed to fly straight home from (x, y)"""
        d = np.maximum(np.hypot(np.asarray(x) - self.home[0], np.asarray(y) - self.home[1]), 1e-6)
        rise = np.maximum(self.home_alt - self.elev(x, y), 0.0)
        ang = np.degrees(np.arctan2(rise, d))
        m = self.model.mass_empty_kg + (liq if self.use_mass else E.LIQUID_L / 2)
        return 1.1 * self._power(m, ang, TRANSIT_V) * d / TRANSIT_V

    def gap(self, x, y):
        if len(self.trees) == 0:
            return np.full(len(x), 99.0)
        d = np.hypot(np.asarray(x)[:, None] - self.trees[None, :, 0], np.asarray(y)[:, None] - self.trees[None, :, 1])
        return (d - self.rad[None, :]).min(1)

    # ---------------------------------------------------------------- flying a list of pieces
    def simulate(self, pieces, record=False):
        S = dict(pos=self.home.copy(), liq=E.LIQUID_L, bat=100.0, sortie=1, fresh=True,
                 e_spray=0.0, e_transit=0.0, len_spray=0.0, len_transit=0.0, contact=0, min_gap=99.0,
                 spray=[], rec=[], sortie_e={1: 0.0})

        def commit(x, y, v, spraying, k=None):
            n = len(x) - 1
            k = n if k is None else k
            if n < 1 or k < 1:
                return
            cost, liq = self.costs(x, y, v, S["liq"], spraying)
            c = float(cost[:k].sum())
            dist = float(np.hypot(np.diff(x[:k + 1]), np.diff(y[:k + 1])).sum())
            g = self.gap(x[:k + 1], y[:k + 1])
            S["contact"] += int((g < E.COLLIDE_M).sum())
            S["min_gap"] = min(S["min_gap"], float(g.min()))
            if record:
                bat = S["bat"] - np.r_[0.0, np.cumsum(cost[:k])]
                S["rec"].append(dict(kind="spray" if spraying else "transit", sortie=S["sortie"],
                                     x=np.round(x[:k + 1], 2).tolist(), y=np.round(y[:k + 1], 2).tolist(),
                                     alt=np.round(self.elev(x[:k + 1], y[:k + 1]) + H_AGL, 2).tolist(),
                                     liq=np.round(liq[:k + 1], 3).tolist(), bat=np.round(bat, 3).tolist()))
            S["bat"] -= c
            S["sortie_e"][S["sortie"]] += c
            S["liq"] = float(liq[k])
            S["pos"] = np.array([x[k], y[k]])
            if spraying:
                S["e_spray"] += c; S["len_spray"] += dist; S["fresh"] = False
                S["spray"].append((x[:k + 1].copy(), y[:k + 1].copy(), S["sortie"]))
            else:
                S["e_transit"] += c; S["len_transit"] += dist

        def go(target):
            x, y = self.dense(self.detour(S["pos"], target), TRANSIT_V)
            commit(x, y, TRANSIT_V, False)

        def go_home(new):
            if np.hypot(*(S["pos"] - self.home)) > 0.5:
                go(self.home)
            if new:
                S["liq"], S["bat"], S["pos"] = E.LIQUID_L, 100.0, self.home.copy()
                S["sortie"] += 1; S["sortie_e"][S["sortie"]] = 0.0; S["fresh"] = True

        def to_entry(target):
            if S["liq"] <= 0.05:
                go_home(True)
            x, y = self.dense(self.detour(S["pos"], target), TRANSIT_V)
            if len(x) > 1:
                cost, _ = self.costs(x, y, TRANSIT_V, S["liq"], False)
                if S["bat"] - cost.sum() - float(np.ravel(self.ret_cost(target[0], target[1], S["liq"]))[0]) < self.reserve:
                    go_home(True)
            go(target)

        for xs, ys in pieces:
            to_entry((xs[0], ys[0]))
            idx = 0
            while idx < len(xs) - 1:
                sx, sy = xs[idx:], ys[idx:]
                cost, liq = self.costs(sx, sy, SPRAY_V, S["liq"], True)
                bat_after = S["bat"] - np.cumsum(cost)
                bad = bat_after - self.ret_cost(sx[1:], sy[1:], liq[1:]) < self.reserve
                kb = int(np.argmax(bad)) if bad.any() else len(cost)
                emp = liq[1:] <= 0.05
                kt = int(np.argmax(emp)) + 1 if emp.any() else len(cost)
                k = min(kb, kt)
                if k == 0:
                    if S["fresh"]:
                        raise RuntimeError("field point cannot be reached with the battery reserve")
                    go_home(True); to_entry((sx[0], sy[0])); continue
                commit(sx, sy, SPRAY_V, True, k)
                idx += k
                if idx < len(xs) - 1:
                    go_home(True); to_entry((xs[idx], ys[idx]))
        go_home(False)
        return S

    # ---------------------------------------------------------------- scoring
    def coverage(self, S, exclude_trees=True, rect=None, upto_sortie=None):
        x0, y0, x1, y1 = rect or self.field
        cx = np.arange(x0 + E.COV_DX / 2, x1, E.COV_DX)
        cy = np.arange(y0 + E.COV_DX / 2, y1, E.COV_DX)
        gx, gy = np.meshgrid(cx, cy, indexing="ij")
        cells = np.stack([gx.ravel(), gy.ravel()], 1)
        ok = np.ones(len(cells), bool)
        if exclude_trees and len(self.trees):
            d = np.hypot(cells[:, None, 0] - self.trees[None, :, 0], cells[:, None, 1] - self.trees[None, :, 1])
            ok = ~(d < self.rad[None, :]).any(1)
        pts = [np.stack([a, b], 1) for a, b, s in S["spray"] if upto_sortie is None or s <= upto_sortie]
        if not pts:
            return 0.0, 0.0, cells[ok]
        dist, _ = cKDTree(np.concatenate(pts)).query(cells, distance_upper_bound=E.SWATH_M / 2)
        cov = np.isfinite(dist)
        return float((cov & ok).sum() / max(ok.sum(), 1)), float((cov & ok).sum() * E.COV_DX ** 2 / 1e4), cells[ok]

    def summary(self, name, S):
        frac, area, _ = self.coverage(S)
        e = sum(S["sortie_e"].values())
        return dict(name=name, energy_pct=e, sorties=S["sortie"] if S["spray"] else 0, coverage=frac,
                    area_ha=area, ha_per_100pct=area * 100.0 / max(e, 1e-9), contact_steps=S["contact"],
                    min_gap_m=S["min_gap"], spray_m=S["len_spray"], transit_m=S["len_transit"],
                    minutes=(S["len_spray"] / SPRAY_V + S["len_transit"] / TRANSIT_V) / 60.0,
                    e_spray=S["e_spray"], e_transit=S["e_transit"])

    # ---------------------------------------------------------------- plans from a block order
    def pieces_for(self, order, axes):
        pieces, pos = [], tuple(self.home)
        for b in order:
            x, y, pos = self.piece(self.blocks[b]["rect"], axes[b], pos)
            pieces.append((x, y))
        return pieces

    def run_order(self, order, axes, record=False):
        return self.simulate(self.pieces_for(order, axes), record)

    def lawnmower(self, detour, axis=0):
        x, y, _ = self.piece(self.field, axis, tuple(self.home), use_detour=detour)
        return [(x, y)]


def load_patch(seed, n_trees=None):
    if n_trees is not None:
        E.N_TREES = n_trees
    env = TeaSprayEnv(seed=seed)
    env.reset(seed=seed)
    return env


def planner_from_env(env, **kw):
    return Planner(env.z, env.trees, env.tree_r, env.model, **kw)


# =====================================================================
def validate(seeds):
    """planner scorer vs the simulator on the plain lawnmower (no trees avoided, first tank only)"""
    print("VALIDATION: planner scorer vs simulator, plain lawnmower, first tank, whole 200 m patch")
    print(f"{'seed':>6s} {'sim battery %':>14s} {'plan battery %':>15s} {'diff':>7s} {'sim ha':>8s} {'plan ha':>8s}")
    diffs = []
    for s in seeds:
        env = TeaSprayEnv(terminate_on_collision=False)
        pol = E.LawnmowerPolicy()
        pol.reset()
        info = E.run_episode(env, lambda o: pol.act(env), s)
        sim_b, sim_a = 100.0 - env.battery, info["area_ha"]
        pl = planner_from_env(env, field=(0, 0, 200, 200), spacing=6.0, reserve=0.0)
        rows = []
        for k in range(34):
            yy = 3.0 + 6.0 * k
            rows += [(3.0, yy), (197.0, yy)] if k % 2 == 0 else [(197.0, yy), (3.0, yy)]
        x, y = Planner.dense([(5.0, 5.0)] + rows, SPRAY_V)
        S = pl.simulate([(x, y)])
        # energy of the spraying part of the first tank only (the flight home is excluded, as in the simulator)
        first_spray = float(pl.costs(*[np.concatenate([a for a, b, s_ in S["spray"] if s_ == 1]),
                                       np.concatenate([b for a, b, s_ in S["spray"] if s_ == 1])], SPRAY_V, E.LIQUID_L, True)[0].sum())
        _, area, _ = pl.coverage(S, exclude_trees=False, rect=(0, 0, 200, 200), upto_sortie=1)
        d = (first_spray / sim_b - 1) * 100
        diffs.append(d)
        print(f"{s:6d} {sim_b:14.2f} {first_spray:15.2f} {d:+6.1f}% {sim_a:8.3f} {area:8.3f}")
    print(f"mean difference {np.mean(diffs):+.1f}%   (the scorer should be within about 1-3%)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=7000)
    ap.add_argument("--field", type=float, nargs=4, default=[10, 10, 110, 110], metavar=("X0", "Y0", "X1", "Y1"))
    ap.add_argument("--block", type=float, default=25.0, help="block side for the grid layout (m)")
    ap.add_argument("--band", type=float, default=20.0, help="band width for the long-row layouts (m)")
    ap.add_argument("--spacing", type=float, default=5.5, help="distance between sweep lines (m), same for every route")
    ap.add_argument("--trees", type=int, default=None)
    ap.add_argument("--iters", type=int, default=300, help="search steps for the optimised order")
    ap.add_argument("--reserve", type=float, default=15.0, help="battery %% kept after flying home")
    ap.add_argument("--z-scale", type=float, default=1.0, help="TEST ONLY: multiply the height differences (to try steeper ground)")
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--out", default=f"{BASE}/planner_output")
    a = ap.parse_args()
    a.field = [float(v) for v in a.field]
    if a.validate:
        validate([6000, 6001, 6002, 6003, 6004, 6005]); return

    env = load_patch(a.seed, a.trees)
    if a.z_scale != 1.0:
        env.z = env.z.mean() + (env.z - env.z.mean()) * a.z_scale
        print(f"NOTE: heights exaggerated x{a.z_scale} for testing - not real terrain")
    pl = planner_from_env(env, field=a.field, block=a.block, spacing=a.spacing, reserve=a.reserve)
    print(f"patch seed {a.seed}: field {a.field}, {len(pl.trees)} trees, mean slope {pl.slope.mean():.1f} deg")
    en = lambda S: sum(S["sortie_e"].values()) + 1000.0 * S["contact"]
    sims, orders, blocks_of = {}, {}, {}

    sims["lawnmower (no avoidance)"] = pl.simulate(pl.lawnmower(False, 0), True)
    sims["lawnmower + detour"] = pl.simulate(pl.lawnmower(True, 0), True)
    best_dir = min((0, 1), key=lambda ax: en(pl.simulate(pl.lawnmower(True, ax))))
    sims["lawnmower + detour, best direction"] = pl.simulate(pl.lawnmower(True, best_dir), True)

    layouts = [("grid", a.block), ("bands_y", a.band), ("bands_x", a.band)]
    for lay, size in layouts:
        pl.blocks = pl._make_blocks(size, lay)
        nb = len(pl.blocks)
        sl = np.array([b["slope"] for b in pl.blocks])
        print(f"\nlayout {lay}: {nb} blocks, slope {sl.min():.1f}-{sl.max():.1f} deg (mean {sl.mean():.1f})")
        cen = np.array([b["centre"] for b in pl.blocks])
        snake = []
        for k, xv in enumerate(sorted(set(np.round(cen[:, 0], 3)))):
            col = [b["id"] for b in pl.blocks if abs(b["centre"][0] - xv) < 1e-3]
            col.sort(key=lambda i: pl.blocks[i]["centre"][1], reverse=bool(k % 2))
            snake += col

        def nearest():
            left, pos, out = set(range(nb)), pl.home, []
            while left:
                j = min(left, key=lambda i: np.hypot(*(np.array(pl.blocks[i]["centre"]) - pos)))
                out.append(j); left.remove(j); pos = np.array(pl.blocks[j]["centre"])
            return out

        def flat_greedy(lam):
            left, pos, out = set(range(nb)), pl.home, []
            D = np.hypot(a.field[2] - a.field[0], a.field[3] - a.field[1])
            while left:
                j = min(left, key=lambda i: np.hypot(*(np.array(pl.blocks[i]["centre"]) - pos)) / D
                        + lam * (sl[i] - sl.min()) / max(np.ptp(sl), 1e-6))
                out.append(j); left.remove(j); pos = np.array(pl.blocks[j]["centre"])
            return out

        long_ax = {"grid": None, "bands_y": 0, "bands_x": 1}[lay]
        if long_ax is None:
            ax_try = [[0] * nb, [1] * nb]
            axes0 = min(ax_try, key=lambda ax: en(pl.run_order(snake, ax)))
        else:
            axes0 = [long_ax] * nb
        cands = {"snake": (snake, axes0), "flat first (sorted)": (list(np.argsort(sl)), axes0),
                 "steep first (sorted)": (list(np.argsort(-sl)), axes0), "flat first + nearby": (flat_greedy(0.5), axes0)}
        if lay == "grid":
            cands["nearest block"] = (nearest(), axes0)
        local = {}
        for k, (o, ax) in cands.items():
            local[f"{lay}: {k}"] = (list(o), list(ax), pl.run_order(o, ax, True))
        start = min(local, key=lambda k: en(local[k][2]))
        order, axes, best = list(local[start][0]), list(local[start][1]), en(local[start][2])
        rng = np.random.default_rng(0)
        for it in range(a.iters):
            o2, a2 = list(order), list(axes)
            r = rng.random()
            if nb < 2:
                break
            if r < 0.45:
                i, j = rng.choice(nb, 2, replace=False); o2[i], o2[j] = o2[j], o2[i]
            elif r < 0.8:
                i, j = rng.choice(nb, 2, replace=False); o2.insert(j, o2.pop(i))
            elif lay == "grid":
                b_ = int(rng.integers(nb)); a2[b_] = 1 - a2[b_]
            S = pl.run_order(o2, a2)
            if en(S) < best - 1e-9:
                order, axes, best = o2, a2, en(S)
        local[f"{lay}: searched"] = (order, axes, pl.run_order(order, axes, True))
        for k, (o, ax, S) in local.items():
            sims[k] = S; orders[k] = [int(i) for i in o]; blocks_of[k] = [dict(id=b["id"], rect=list(b["rect"]), slope=b["slope"]) for b in pl.blocks]

    rows = [pl.summary(k, S) for k, S in sims.items()]
    ref = next(r for r in rows if r["name"] == "lawnmower + detour")
    ref2 = next(r for r in rows if r["name"] == "lawnmower + detour, best direction")
    print(f"\n{'route':44s} {'battery %':>9s} {'transit %':>9s} {'sorties':>7s} {'cover':>6s} {'ha/100%':>8s} {'vs detour':>9s} {'vs best dir':>11s} {'contacts':>8s} {'min gap':>7s}")
    for r in rows:
        r["saving_vs_detour_pct"] = (1 - r["energy_pct"] / ref["energy_pct"]) * 100
        r["saving_vs_best_direction_pct"] = (1 - r["energy_pct"] / ref2["energy_pct"]) * 100
        print(f"{r['name']:44s} {r['energy_pct']:9.1f} {r['e_transit']:9.1f} {r['sorties']:7d} {100 * r['coverage']:5.1f}% "
              f"{r['ha_per_100pct']:8.3f} {r['saving_vs_detour_pct']:+8.1f}% {r['saving_vs_best_direction_pct']:+10.1f}% {r['contact_steps']:8d} {r['min_gap_m']:7.1f}")

    ok = [r for r in rows if r["contact_steps"] == 0 and r["coverage"] >= 0.98]
    best_row = min(ok, key=lambda r: r["energy_pct"])
    rec = best_row["name"]
    print(f"\nRECOMMENDED: {rec}  ({best_row['energy_pct']:.1f} % battery, coverage {100 * best_row['coverage']:.1f} %, "
          f"{best_row['saving_vs_detour_pct']:+.1f} % vs lawnmower+detour, {best_row['saving_vs_best_direction_pct']:+.1f} % vs best-direction)")

    print("\nTank level while spraying on the flattest vs the steepest third of the field")
    for k, S in sims.items():
        liq = []
        for rec_ in S["rec"]:
            if rec_["kind"] == "spray":
                liq += list(zip(rec_["x"], rec_["y"], rec_["liq"]))
        arr = np.array(liq)
        s_here = pl.slope_at(arr[:, 0], arr[:, 1])
        lo, hi = np.percentile(s_here, [33, 67])
        print(f"  {k:44s} flat third {100 * arr[s_here <= lo, 2].mean() / E.LIQUID_L:5.1f}% full | "
              f"steep third {100 * arr[s_here >= hi, 2].mean() / E.LIQUID_L:5.1f}% full")

    os.makedirs(a.out, exist_ok=True)
    out = dict(seed=a.seed, field=a.field, home=list(pl.home), block=a.block, spacing=a.spacing,
               terrain=dict(dx=E.TERRAIN_DX, z=np.round(env.z, 2).tolist()),
               trees=[dict(x=float(t[0]), y=float(t[1]), r=float(r)) for t, r in zip(pl.trees, pl.rad)],
               recommended=rec, blocks_of=blocks_of, orders=orders,
               slope=np.round(pl.slope, 2).tolist(),
               summary=rows, plans={k: S["rec"] for k, S in sims.items()},
               settings=dict(h_agl=H_AGL, spray_v=SPRAY_V, transit_v=TRANSIT_V, reserve=a.reserve,
                             tank_l=E.LIQUID_L, l_per_m=E.L_PER_M, mass_empty=pl.model.mass_empty_kg))
    p = f"{a.out}/plan_{a.seed}.json"
    json.dump(out, open(p, "w"), default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print(f"\nSaved {p}  ({os.path.getsize(p) / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()