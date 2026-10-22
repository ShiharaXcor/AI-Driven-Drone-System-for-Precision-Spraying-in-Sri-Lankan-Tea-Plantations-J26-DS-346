# engine.py - Component 3 mission planning engine (energy-aware, mass-aware, collision-free routes)
#
# What it does
#   Takes a site (real SRTM terrain), a field polygon, trees, a refill point (depot) and drone settings, and builds
#   complete missions: serpentine rows over the polygon, arcs around every tree, refill sorties, battery reserve.
#   Every mission is scored with the SAME calibrated energy model used in the simulator
#   (hover power grows with the mass: P_hover ~ (m g)^1.5, plus climb and drag), with the tank mass falling as liquid
#   is sprayed.
#
#   Strategies compared on the SAME field with the SAME row spacing and coverage check:
#     fixed    - rows along the longest field edge, no tree avoidance (what a plain waypoint mission does)
#     standard - rows along the longest edge, tree arcs, full tank at every refill
#     optimised- searched row direction and start corner, load-levelled refills (carry only the liquid still needed)
#   plus lever tests (each lever alone), a refill-point advisor and a speed what-if.
#
# Assumptions are listed in ASSUMPTIONS and shown in the app. The energy model is fitted to SULEKO / Kenilworth
# figures; it is NOT validated on a real field yet.

import os, sys, json, math, time, glob
import numpy as np
from scipy.ndimage import map_coordinates
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))


def _find_drl():
    c = [os.environ.get("C3_DRL")] + [os.path.join(HERE, "..", "..", d) for d in ("drl_agent", "rl_v2")]
    for d in c:
        if d and os.path.exists(os.path.join(d, "tea_spray_env.py")):
            return os.path.abspath(d)
    raise FileNotFoundError("tea_spray_env.py not found: set C3_DRL to the folder that contains it")


sys.path.insert(0, _find_drl())
import tea_spray_env as E   # constants, energy model loader, SRTM loader

SRTM_DX = E.SRTM_DX
GRID = 5.0           # terrain grid (m)
COV_DX = 2.0         # coverage check grid (m)
H_AGL = 3.0          # flight height above the ground (m)
COLLIDE_M = 1.0      # canopy contact distance (m)

ASSUMPTIONS = [
    "Energy: calibrated hover + climb + drag model (fitted to Kenilworth and SULEKO figures); not yet validated on a real field.",
    "Terrain: SRTM 90 m elevation interpolated to a 5 m grid; real tea slopes are probably steeper than this smooth data shows.",
    "Spray dose is held at 0.0306 L per metre of row (about 51 L/ha at a 6 m swath); the pump follows the speed.",
    "Row turns are flown at a slow turn speed with the nozzle closed; refills happen at the depot with a fast transit flight.",
    "Trees are circles. The route keeps a clearance margin around each canopy (default 3.5 m); contact is counted inside 1 m.",
    "Battery reserve is kept after the flight back to the depot, estimated as a straight flight with a 10% allowance.",
]


# ------------------------------------------------------------------ sites
class Sites:
    """Named terrain windows cut from the SRTM tile (size x size metres)."""

    def __init__(self, size=300.0):
        self.size = size
        self.n = int(size / GRID)
        self.z_srtm, _ = E.load_elevation()
        self.z_srtm = np.nan_to_num(self.z_srtm, nan=float(np.nanmean(self.z_srtm)))
        w = int(math.ceil(size / SRTM_DX)) + 1
        R, C = self.z_srtm.shape
        cand = []
        for r in range(R - w + 1):
            for c in range(C - w + 1):
                win = self.z_srtm[r:r + w, c:c + w]
                gy, gx = np.gradient(win, SRTM_DX)
                cand.append((float(np.degrees(np.arctan(np.hypot(gx, gy))).mean()), r, c))
        cand.sort()
        pick = [cand[int(q * (len(cand) - 1))] for q in (0.10, 0.45, 0.80, 0.97)]
        names = ["Gentle valley floor", "Rolling slope", "Steep hillside", "Ridge and gully"]
        self.defs = []
        for (s, r, c), nm in zip(pick, names):
            self.defs.append(dict(id=f"site-{r}-{c}", name=nm, r=r, c=c, mean_slope=round(s, 1)))
        self.w = w
        self._cache = {}
        self.custom = {}
        self._load_custom()

    # ---- estates added from latitude/longitude or a KML file
    @staticmethod
    def _cache_dir():
        d = os.environ.get("C3_CACHE", os.path.abspath(os.path.join(HERE, "..", "cache")))
        os.makedirs(d, exist_ok=True)
        return d

    def _load_custom(self):
        for fn in glob.glob(os.path.join(self._cache_dir(), "site_*.json")):
            try:
                d = json.load(open(fn))
                d["z"] = np.asarray(d["z"], float)
                self.custom[d["id"]] = d
            except Exception:
                pass

    def add_custom(self, sid, name, size, z, lat0, lon0, imagery=False):
        d = dict(id=sid, name=name, size=float(size), z=np.asarray(z, float), lat0=lat0, lon0=lon0, imagery=imagery, custom=True)
        self.custom[sid] = d
        out = dict(d, z=np.round(d["z"], 2).tolist())
        json.dump(out, open(os.path.join(self._cache_dir(), f"site_{sid}.json"), "w"))
        return d

    def size_of(self, sid):
        if sid in self.custom:
            return self.custom[sid]["size"]
        return self.size

    def meta(self, sid):
        z = self.get(sid)
        gy, gx = np.gradient(z, GRID)
        d = dict(id=sid, size=self.size_of(sid), relief=round(float(z.max() - z.min()), 1), elevation=round(float(z.mean()), 0),
                 mean_slope=round(float(np.degrees(np.arctan(np.hypot(gx, gy))).mean()), 1))
        if sid in self.custom:
            c = self.custom[sid]
            d.update(name=c["name"], custom=True, lat0=c["lat0"], lon0=c["lon0"], imagery=bool(c.get("imagery")))
        else:
            d["name"] = next(x["name"] for x in self.defs if x["id"] == sid)
        return d

    def get(self, sid, z_scale=1.0):
        if sid in self.custom:
            z = self.custom[sid]["z"]
            return z.mean() + (z - z.mean()) * z_scale if z_scale != 1.0 else z
        d = next(x for x in self.defs if x["id"] == sid)
        key = (sid, round(z_scale, 3))
        if key not in self._cache:
            win = self.z_srtm[d["r"]:d["r"] + self.w, d["c"]:d["c"] + self.w]
            pos = (np.arange(self.n) + 0.5) * GRID / SRTM_DX
            ii, jj = np.meshgrid(pos, pos, indexing="ij")
            z = map_coordinates(win, [ii, jj], order=3, mode="nearest")
            if z_scale != 1.0:
                z = z.mean() + (z - z.mean()) * z_scale
            self._cache[key] = z
        return self._cache[key]

    def listing(self):
        out = []
        for d in self.defs:
            z = self.get(d["id"])
            out.append(dict(d, size=self.size, relief=round(float(z.max() - z.min()), 1),
                            elevation=round(float(z.mean()), 0)))
        for sid in self.custom:
            out.append(self.meta(sid))
        return out


# ------------------------------------------------------------------ geometry helpers
def point_in_poly(px, py, poly):
    inside = np.zeros(np.shape(px), bool)
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        cond = (y1 > py) != (y2 > py)
        with np.errstate(divide="ignore", invalid="ignore"):
            xi = (x2 - x1) * (py - y1) / (y2 - y1) + x1
        inside ^= cond & (px < xi)
    return inside


def poly_area(poly):
    p = np.asarray(poly, float)
    x, y = p[:, 0], p[:, 1]
    return 0.5 * abs(float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))))


def poly_centroid(poly):
    return np.asarray(poly, float).mean(0)


def longest_edge_deg(poly):
    """row direction of a plain mission planner: along the longest field edge"""
    p = np.asarray(poly, float)
    q = np.roll(p, -1, axis=0)
    d = q - p
    k = int(np.argmax(np.hypot(d[:, 0], d[:, 1])))
    return float(math.degrees(math.atan2(d[k, 1], d[k, 0])) % 180.0)


def rot(p, th):
    c, s = math.cos(th), math.sin(th)
    p = np.asarray(p, float)
    return np.stack([c * p[..., 0] - s * p[..., 1], s * p[..., 0] + c * p[..., 1]], -1)


# ------------------------------------------------------------------ the planning problem
class Problem:
    def __init__(self, z, poly, trees, depot, par, model):
        self.z = z
        self.poly = np.asarray(poly, float)
        self.trees = np.asarray([[t["x"], t["y"]] for t in trees], float).reshape(-1, 2)
        self.rad = np.asarray([t["r"] for t in trees], float)
        self.depot = np.asarray(depot, float)
        self.par = par
        self.model = model
        self.vs = par["spray_kmh"] / 3.6
        self.vt = par["transit_kmh"] / 3.6
        self.vturn = par["turn_kmh"] / 3.6
        self.swath = par["swath"]
        self.spacing = par["swath"] * 0.92
        self.tank = par["tank_l"]
        self.l_per_m = par["l_per_ha"] * self.swath / 10000.0
        self.reserve = par["reserve"]
        self.refill_s = float(par.get("refill_s", 0.0))
        self.margin = par["clearance"]
        self.centre = poly_centroid(self.poly)
        self.home_alt = float(self.elev(*self.depot)[0])

    # world-frame terrain
    def elev(self, x, y):
        x, y = np.atleast_1d(np.asarray(x, float)), np.atleast_1d(np.asarray(y, float))
        shp = np.broadcast(x, y).shape
        r = map_coordinates(self.z, [np.broadcast_to(x, shp).ravel() / GRID - 0.5,
                                     np.broadcast_to(y, shp).ravel() / GRID - 0.5], order=1, mode="nearest")
        return r.reshape(shp)

    def power(self, m, ang_deg, v):
        mdl = self.model
        s = np.radians(np.clip(ang_deg, 0, 60))
        p = mdl.hover_power(m) + np.maximum(0.0, m * mdl.g * v * np.sin(s) * mdl.k_climb) + 0.5 * mdl.k_drag * v ** 2
        return p * mdl.level_scale / 3600.0 / mdl.battery_wh * 100.0          # battery % per second


# ------------------------------------------------------------------ one row direction
class Frame:
    """The problem rotated by -theta about the field centre: rows run along local x."""

    def __init__(self, P, theta_deg):
        self.P, self.th = P, math.radians(theta_deg)
        self.theta_deg = theta_deg
        c = P.centre
        self.poly = rot(P.poly - c, -self.th)
        self.trees = rot(P.trees - c, -self.th) if len(P.trees) else P.trees
        self.rad = P.rad
        self.depot = rot(P.depot - c, -self.th)
        self._cache = {}

    def to_world(self, x, y):
        p = rot(np.stack([np.asarray(x, float), np.asarray(y, float)], -1), self.th) + self.P.centre
        return p[..., 0], p[..., 1]

    def elev(self, x, y):
        wx, wy = self.to_world(x, y)
        return self.P.elev(wx, wy)

    # --- trees
    def detour(self, a, b, depth=0):
        """cached: the same leg is asked for again and again when a mission is replayed (agent training)"""
        key = (round(float(a[0]), 4), round(float(a[1]), 4), round(float(b[0]), 4), round(float(b[1]), 4), depth)
        cache = self._cache.setdefault("det", {})
        r = cache.get(key)
        if r is None:
            r = cache[key] = self._detour(a, b, depth)
        return r

    def _detour(self, a, b, depth=0):
        a, b = np.asarray(a, float), np.asarray(b, float)
        d = b - a
        L = float(np.hypot(*d))
        if L < 1e-6 or depth > 6 or len(self.trees) == 0:
            return [a, b]
        u = d / L
        best = None
        for c, r in zip(self.trees, self.rad):
            R = r + self.P.margin
            for e in (a, b):
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
        nn = n if np.dot(c - a, n) <= 0 else -n
        Rp = 1.15 * R
        wp = [c + Rp * (-u * np.cos(np.radians(f)) + nn * np.sin(np.radians(f))) for f in (35, 90, 145)]
        chain = [a] + wp + [b]
        out = [a]
        for p, q in zip(chain[:-1], chain[1:]):
            out += self.detour(p, q, depth + 1)[1:]
        return out

    def row_path(self, a, b, o, avoid=True):
        """straight row along local x at height o from a to b with an arc round every tree buffer"""
        sgn = 1.0 if b >= a else -1.0
        if avoid:
            for _ in range(3):               # a row end inside a tree buffer is moved to the buffer edge
                moved = False
                for (cx, cy), r in zip(self.trees, self.rad):
                    R = r + self.P.margin
                    dy = o - cy
                    if abs(dy) >= R * 0.98:
                        continue
                    h = math.sqrt(max(R * R - dy * dy, 0.0))
                    if (cx - h - a) * sgn <= 0 <= (cx + h - a) * sgn and (cx + h - a) * sgn > 0:
                        a = cx + h if sgn > 0 else cx - h
                        a += 0.05 * sgn; moved = True
                    if (cx - h - b) * sgn <= 0 <= (cx + h - b) * sgn:
                        b = cx - h if sgn > 0 else cx + h
                        b -= 0.05 * sgn; moved = True
                if not moved:
                    break
            if (b - a) * sgn <= 0.5:
                return [np.array([a, o], float), np.array([a, o], float)]
        lo, hi = min(a, b), max(a, b)
        pts, last = [(a, o)], -1e9
        if avoid:
            hits = []
            for (cx, cy), r in zip(self.trees, self.rad):
                R = r + self.P.margin
                dy = o - cy
                if abs(dy) >= R * 0.98:
                    continue
                h = math.sqrt(max(R * R - dy * dy, 0.0))
                if cx + h < lo or cx - h > hi:
                    continue
                hits.append((cx, cy, R, dy, h))
            hits.sort(key=lambda t: t[0] * sgn)
            for cx, cy, R, dy, h in hits:
                e1, e2 = (cx - h, cx + h) if sgn > 0 else (cx + h, cx - h)
                if last != -1e9 and e1 * sgn < last * sgn + 1e-9:
                    continue
                th1, th2 = math.atan2(dy, e1 - cx), math.atan2(dy, e2 - cx)
                if (e1 - a) * sgn >= 0:
                    pts.append((e1, o))
                n_arc = max(2, int(abs(th2 - th1) / math.radians(15)))
                for t in np.linspace(th1, th2, n_arc + 1)[1:-1]:
                    pts.append((cx + R * math.cos(t), cy + R * math.sin(t)))
                pts.append((e2, o))
                last = e2
        pts.append((b, o))
        return [np.array(p, float) for p in pts]

    # --- rows
    def rows(self):
        """list of rows: (y, [(x0, x1), ...]) with the strip's own extent, bottom to top"""
        if "rows" in self._cache:
            return self._cache["rows"]
        ys = self.poly[:, 1]
        y0, y1 = ys.min(), ys.max()
        n = max(1, int(math.ceil((y1 - y0) / self.P.spacing - 1e-6)))
        sp = (y1 - y0) / n

        def cross(yy):
            xs = []
            m = len(self.poly)
            for i in range(m):
                (ax, ay), (bx, by) = self.poly[i], self.poly[(i + 1) % m]
                if (ay > yy) != (by > yy):
                    xs.append(ax + (bx - ax) * (yy - ay) / (by - ay))
            xs.sort()
            return [(xs[k], xs[k + 1]) for k in range(0, len(xs) - 1, 2)]

        out = []
        for k in range(n):
            yc = y0 + (k + 0.5) * sp
            iv = []
            for yy in (yc - sp / 2 + 1e-3, yc, yc + sp / 2 - 1e-3):
                iv += cross(yy)
            iv.sort()
            merged = []
            for a, b in iv:
                if merged and a <= merged[-1][1] + 1.0:
                    merged[-1][1] = max(merged[-1][1], b)
                else:
                    merged.append([a, b])
            merged = [(a, b) for a, b in merged if b - a > 1.0]
            if merged:
                out.append((yc, merged))
        self._cache["rows"] = out
        return out

    def build(self, flip_rows, flip_dir, avoid=True, start=None, order=None):
        """one continuous path: arrays x, y, v, spray(bool) along dense points (about 1 s apart).
        order: optional list of row numbers (into rows()) giving the order the rows are sprayed in (used by the flat-first strategy)"""
        key = ("path", flip_rows, flip_dir, avoid, None if order is None else tuple(order))
        if key in self._cache:
            return self._cache[key]
        P = self.P
        allrows = self.rows()
        if order is not None:
            rows = [allrows[j] for j in order]
        else:
            rows = allrows[::-1] if flip_rows else allrows
        segs = []                                   # (points, speed, spraying, row number)
        last = None
        rn = 0
        for i, (yc, ivs) in enumerate(rows):
            fwd = (i % 2 == 0) != flip_dir
            seq = ivs if fwd else ivs[::-1]
            for a, b in seq:
                p, q = (a, b) if fwd else (b, a)
                if last is not None:
                    conn = [last, np.array([p, yc])]
                    if avoid:
                        conn = self.detour(last, np.array([p, yc]))
                    length = sum(float(np.hypot(*(conn[j + 1] - conn[j]))) for j in range(len(conn) - 1))
                    segs.append((conn, P.vt if length > 12.0 else P.vturn, False, rn))
                rp = self.row_path(p, q, yc, avoid)
                if last is not None and (rp[0][0] != p):
                    conn = self.detour(last, rp[0]) if avoid else [last, rp[0]]
                    length = sum(float(np.hypot(*(conn[j + 1] - conn[j]))) for j in range(len(conn) - 1))
                    segs[-1] = (conn, P.vt if length > 12.0 else P.vturn, False, rn)
                segs.append((rp, P.vs, True, rn))
                rn += 1
                last = rp[-1]
        X, Y, V, S, RID = [segs[0][0][0][0]], [segs[0][0][0][1]], [], [], []
        for pts, v, sp, rn_ in segs:
            x, y = self.dense(pts, v * 1.0)
            X += list(x[1:]); Y += list(y[1:])
            V += [v] * (len(x) - 1); S += [sp] * (len(x) - 1); RID += [rn_] * (len(x) - 1)
        out = (np.array(X), np.array(Y), np.array(V), np.array(S, bool), np.array(RID))
        self._cache[key] = out
        return out

    @staticmethod
    def dense(path, step):
        Q = np.asarray(path, float)
        seg = np.hypot(*np.diff(Q, axis=0).T)
        c = np.r_[0.0, np.cumsum(seg)]
        if c[-1] < 1e-9:
            return Q[:1, 0], Q[:1, 1]
        n = max(1, int(math.ceil(c[-1] / step)))
        s = np.linspace(0, c[-1], n + 1)
        return np.interp(s, c, Q[:, 0]), np.interp(s, c, Q[:, 1])


# ------------------------------------------------------------------ flying a path
class Flight:
    def __init__(self, fr):
        self.fr, self.P = fr, fr.P

    def costs(self, x, y, v, spray, liq0):
        P = self.P
        d = np.hypot(np.diff(x), np.diff(y))
        vv = np.asarray(v, float)
        dt = np.maximum(d, 1e-9) / vv
        alt = self.fr.elev(x, y) + H_AGL
        rr = np.maximum(np.diff(alt) / dt, 0.0)
        ang = np.minimum(np.degrees(np.arctan2(rr, np.maximum(vv, 0.2))), 60.0)
        used = np.r_[0.0, np.cumsum(P.l_per_m * d * spray)]
        liq = np.maximum(liq0 - used, 0.0)
        m = P.model.mass_empty_kg + liq[:-1]
        return P.power(m, ang, vv) * dt, liq, dt

    def ret_cost(self, x, y, liq):
        P = self.P
        d = np.maximum(np.hypot(np.asarray(x) - self.fr.depot[0], np.asarray(y) - self.fr.depot[1]), 1e-6)
        rise = np.maximum(P.home_alt - self.fr.elev(x, y), 0.0)
        ang = np.degrees(np.arctan2(rise, d))
        return 1.1 * P.power(P.model.mass_empty_kg + liq, ang, P.vt) * d / P.vt

    def gap(self, x, y):
        t = self.fr.trees
        if len(t) == 0:
            return np.full(len(x), 99.0)
        d = np.hypot(np.asarray(x)[:, None] - t[None, :, 0], np.asarray(y)[:, None] - t[None, :, 1])
        return (d - self.fr.rad[None, :]).min(1)

    def run(self, path, exact_fill=True, state=None, record=False):
        """fly the path; refill at the depot when the tank or the battery requires it"""
        fr, P = self.fr, self.P
        x, y, v, sp, rid = path
        n = len(x) - 1
        dstep = np.hypot(np.diff(x), np.diff(y))
        cs = np.r_[0.0, np.cumsum(dstep * sp)]                  # spray metres up to each point
        total = cs[-1]
        dep = fr.depot

        def fill(idx):
            """liquid loaded at the depot. exact_fill = load levelling: split the liquid still needed evenly
            over the sorties still to fly, so no sortie carries more than it must (hover power grows with m^1.5)"""
            need = P.l_per_m * (total - cs[idx]) * 1.02
            if callable(exact_fill):             # a learned agent decides the load (see agent_env.py)
                return float(min(P.tank, max(0.2, exact_fill(dict(idx=int(idx), need=need, S=S, total=total, cs=cs)))))
            if not exact_fill:
                return P.tank
            if exact_fill == "trim":                 # full tanks, only the last one trimmed to what is left
                return min(P.tank, need + 0.2)
            k = max(1, int(math.ceil(need / P.tank - 1e-9)))
            return min(P.tank, need / k + 0.2)

        S = dict(pos=dep.copy(), bat=100.0, liq=0.0, sortie=1, fresh=True, e=dict(spray=0.0, turn=0.0, transit=0.0),
                 sortie_e={1: 0.0}, contact=0, min_gap=99.0, spray=[], rec=[], litres=0.0, sorties_len={}, t=0.0,
                 refills=[], cur=0)
        def overhead():
            """take-off + landing at the depot: refill_s of hover at the mass just loaded (battery %)"""
            ov = P.refill_s * float(P.power(P.model.mass_empty_kg + S["liq"], 0.0, 0.0))
            S["bat"] -= ov
            S["sortie_e"][S["sortie"]] += ov
            S["t"] += P.refill_s

        if state:
            S.update(state)
        else:
            S["liq"] = fill(0)
            overhead()

        def commit(xs, ys, vs, sps, kinds, pid=None):
            if len(xs) < 2:
                return
            cost, liq, dt = self.costs(xs, ys, vs, sps, S["liq"])
            g = self.gap(xs, ys)
            S["contact"] += int((g < COLLIDE_M).sum())
            S["min_gap"] = min(S["min_gap"], float(g.min()))
            S["litres"] += float(S["liq"] - liq[-1])
            for kd, nm in ((1, "spray"), (2, "turn"), (0, "transit")):
                S["e"][nm] += float(cost[np.asarray(kinds) == kd].sum())
            if record:
                bat = S["bat"] - np.r_[0.0, np.cumsum(cost)]
                wx, wy = fr.to_world(xs, ys)
                tt = S["t"] + np.r_[0.0, np.cumsum(dt)]
                pid_ = np.full(len(xs), S["cur"]) if pid is None else pid
                S["rec"].append(dict(sortie=S["sortie"], x=wx, y=wy, alt=fr.elev(xs, ys) + H_AGL, liq=liq, bat=bat,
                                     kind=np.r_[kinds[0], kinds], t=tt, pidx=pid_))
            S["t"] += float(dt.sum())
            S["bat"] -= float(cost.sum())
            S["sortie_e"][S["sortie"]] += float(cost.sum())
            S["liq"] = float(liq[-1])
            S["pos"] = np.array([xs[-1], ys[-1]])
            m = np.asarray(sps, bool)
            if m.any():
                xa, ya = np.asarray(xs, float), np.asarray(ys, float)
                S["spray"].append(np.stack([xa[:-1], ya[:-1], xa[1:], ya[1:]], 1)[m])
            S["fresh"] = False

        def go(target):
            pts = fr.detour(S["pos"], target)
            xs, ys = fr.dense(pts, P.vt * 1.0)
            if len(xs) > 1:
                commit(xs, ys, np.full(len(xs) - 1, P.vt), np.zeros(len(xs) - 1, bool), np.zeros(len(xs) - 1, int))

        def refill(idx):
            S["cur"] = idx
            if np.hypot(*(S["pos"] - dep)) > 0.5:
                go(dep)
            S["refills"].append(dict(x=float(fr.to_world(*dep)[0]), y=float(fr.to_world(*dep)[1]), t=S["t"]))
            S["bat"], S["pos"] = 100.0, dep.copy()
            S["liq"] = fill(idx)
            S["sortie"] += 1
            S["sortie_e"][S["sortie"]] = 0.0
            S["fresh"] = True
            overhead()

        def to_entry(idx):
            S["cur"] = idx
            tgt = np.array([x[idx], y[idx]])
            if S["liq"] <= 0.05 and total - cs[idx] > 0.5:
                refill(idx)
            xs, ys = fr.dense(fr.detour(S["pos"], tgt), P.vt * 1.0)
            if len(xs) > 1:
                cost, _, _ = self.costs(xs, ys, np.full(len(xs) - 1, P.vt), np.zeros(len(xs) - 1, bool), S["liq"])
                if S["bat"] - cost.sum() - float(np.ravel(self.ret_cost(tgt[0], tgt[1], S["liq"]))[0]) < P.reserve:
                    refill(idx)
            go(tgt)

        idx = int(state.get("idx", 0)) if state else 0
        to_entry(idx)
        guard = 0
        while idx < n:
            guard += 1
            if guard > 400:
                raise RuntimeError("mission does not converge (too many refills)")
            xs, ys, vs, sps = x[idx:], y[idx:], v[idx:], sp[idx:]
            cost, liq, _ = self.costs(xs, ys, vs, sps, S["liq"])
            bat_after = S["bat"] - np.cumsum(cost)
            bad = bat_after - self.ret_cost(xs[1:], ys[1:], liq[1:]) < P.reserve
            kb = int(np.argmax(bad)) if bad.any() else len(cost)
            sprayed_so_far = np.cumsum(sps)
            emp = (liq[1:] <= 0.05) & (sprayed_so_far > 0)
            kt = int(np.argmax(emp)) if emp.any() else len(cost)
            k = min(kb, kt, len(cost))
            if k == 0:
                if S["fresh"]:
                    raise RuntimeError("a point of the field cannot be reached with this battery reserve")
                refill(idx)
                to_entry(idx)
                continue
            kinds = np.where(sps[:k], 1, np.where(vs[:k] < P.vt - 1e-6, 2, 0))
            commit(xs[:k + 1], ys[:k + 1], vs[:k], sps[:k], kinds, pid=np.arange(idx, idx + k + 1))
            idx += k
            S["cur"] = idx
            if idx < n:
                refill(idx)
                to_entry(idx)
        if np.hypot(*(S["pos"] - dep)) > 0.5:
            go(dep)
        S["idx"] = idx
        return S

    # ---------------------------------------------------------- scoring
    def coverage(self, S):
        fr = self.fr
        P = self.P
        poly = P.poly
        lo, hi = poly.min(0), poly.max(0)
        cx = np.arange(lo[0] + COV_DX / 2, hi[0], COV_DX)
        cy = np.arange(lo[1] + COV_DX / 2, hi[1], COV_DX)
        gx, gy = np.meshgrid(cx, cy, indexing="ij")
        cells = np.stack([gx.ravel(), gy.ravel()], 1)
        ok = point_in_poly(cells[:, 0], cells[:, 1], poly)
        if len(P.trees):
            d = np.hypot(cells[:, None, 0] - P.trees[None, :, 0], cells[:, None, 1] - P.trees[None, :, 1])
            ok &= ~(d < P.rad[None, :]).any(1)
        if not S["spray"]:
            return 0.0, 0.0, cells[ok]
        seg = np.concatenate(S["spray"])
        L = np.hypot(seg[:, 2] - seg[:, 0], seg[:, 3] - seg[:, 1])
        ns = np.maximum(1, np.ceil(L / 1.0).astype(int))
        idx = np.repeat(np.arange(len(seg)), ns)
        j = np.arange(len(idx)) - np.repeat(np.cumsum(ns) - ns, ns)
        f = ((j + 0.5) / ns[idx])[:, None]
        pts = seg[idx, :2] * (1 - f) + seg[idx, 2:] * f
        wx, wy = fr.to_world(pts[:, 0], pts[:, 1])
        dist, _ = cKDTree(np.stack([wx, wy], 1)).query(cells, distance_upper_bound=P.swath / 2)
        cov = np.isfinite(dist)
        n_ok = max(int(ok.sum()), 1)
        return float((cov & ok).sum() / n_ok), float((cov & ok).sum() * COV_DX ** 2 / 1e4), cells[ok]

    def metrics(self, S):
        P = self.P
        frac, area, _ = self.coverage(S)
        e = sum(S["sortie_e"].values())
        t_spray = sum(len(a) for a in S["spray"])      # about one second per point
        return dict(energy_pct=e, sorties=S["sortie"], coverage=frac, area_ha=area,
                    ha_per_100pct=area * 100.0 / max(e, 1e-9), contact_steps=S["contact"],
                    min_gap_m=S["min_gap"], litres=S["litres"], minutes=S["t"] / 60.0,
                    e_spray=S["e"]["spray"], e_turn=S["e"]["turn"], e_transit=S["e"]["transit"])


# ------------------------------------------------------------------ planner API
DEFAULTS = dict(spray_kmh=6.4, transit_kmh=25.2, turn_kmh=5.4, swath=6.0, l_per_ha=51.0, tank_l=20.0,
                reserve=15.0, clearance=3.5, refill_s=40.0)   # refill_s: take-off + landing time per sortie, hover at the loaded mass.
                                                            # 40 s is about 8 % battery; with the transit legs the fixed cost per sortie is about 12 %,
                                                            # close to the 13.4 % intercept measured in 667 real sorties (battery drop vs litres)


class MissionPlanner:
    def __init__(self, sites=None):
        self.sites = sites or Sites()
        import energy_scenario as _ES
        self.model = _ES.apply(E.load_model())

    # ---- helpers
    def problem(self, req):
        par = dict(DEFAULTS)
        par.update({k: float(v) for k, v in (req.get("params") or {}).items() if k in DEFAULTS})
        z = self.sites.get(req["site"], float(req.get("z_scale", 1.0)))
        P = Problem(z, req["polygon"], req.get("trees", []), req["depot"], par, self.model)
        return P

    def _best(self, P, theta, exact, avoid=True):
        fr = Frame(P, theta)
        fl = Flight(fr)
        best = None
        for fr_, fd in ((False, False), (False, True), (True, False), (True, True)):
            path = fr.build(fr_, fd, avoid)
            S = fl.run(path, exact)
            e = sum(S["sortie_e"].values()) + 1000.0 * S["contact"]
            if best is None or e < best[0]:
                best = (e, fr_, fd, S)
        return best[1], best[2], best[3], fr, fl

    def _pack(self, P, name, theta, fr_, fd, exact, avoid=True, record=True, order=None):
        fr = Frame(P, theta)
        fl = Flight(fr)
        S = fl.run(fr.build(fr_, fd, avoid, order=order), exact, record=record)
        m = fl.metrics(S)
        m.update(name=name, theta=theta, exact_fill=str(exact), avoid=avoid)
        return m, S, fl

    @staticmethod
    def _slope_load(strats, P):
        """Where does each route climb: with a heavy tank or a light one? (spraying legs only)"""
        gx, gy = np.gradient(P.z, GRID)
        slope = np.degrees(np.arctan(np.hypot(gx, gy)))
        m_empty, tank = float(P.model.mass_empty_kg), float(P.tank)
        out = {}
        for s in strats:
            if s["id"] not in ("standard", "optimised", "agent", "flatfirst"):
                continue
            r = s["route"]
            x, y = np.asarray(r["x"], float), np.asarray(r["y"], float)
            liq, kind = np.asarray(r["liq"], float), np.asarray(r["kind"])
            if len(x) < 3:
                continue
            z = P.elev(x, y)
            sl = map_coordinates(slope, [x / GRID - 0.5, y / GRID - 0.5], order=1, mode="nearest")
            dz = np.diff(z)
            up = np.maximum(dz, 0.0)
            seg_kind = (kind[1:] == 1) & (kind[:-1] == 1)             # spraying legs
            lq = 0.5 * (liq[1:] + liq[:-1])
            sls = 0.5 * (sl[1:] + sl[:-1])
            heavy, light = seg_kind & (lq > tank * 2 / 3), seg_kind & (lq < tank / 3)

            def mean_sl(mk):
                return float(sls[mk].mean()) if mk.any() else None
            out[s["id"]] = dict(
                slope_heavy=mean_sl(heavy), slope_light=mean_sl(light),
                climb_heavy_m=float(up[heavy].sum()), climb_light_m=float(up[light].sum()),
                climb_total_m=float(up[seg_kind].sum()),
                mass_climb=float((up * (m_empty + lq))[seg_kind].sum()),      # kg x m climbed while spraying
                share_heavy=float(heavy.sum() / max(seg_kind.sum(), 1)), share_light=float(light.sum() / max(seg_kind.sum(), 1)))
        return out

    @staticmethod
    def _route_advice(strats, rec, P, bat_wh):
        """Plain-language answer to: should the pilot fly the usual route or the system's route?"""
        by = {s["id"]: s["metrics"] for s in strats}
        usual, mine = by["standard"], by[rec]
        area = max(float(usual["area_ha"]), 1e-6)
        sav = (1 - mine["energy_pct"] / usual["energy_pct"]) * 100 if usual["energy_pct"] > 0 else 0.0
        wh = (usual["energy_pct"] - mine["energy_pct"]) / 100.0 * bat_wh
        d_sort = int(mine["sorties"] - usual["sorties"])
        d_min = float(mine["minutes"] - usual["minutes"])
        safe = mine["contact_steps"] == 0 and mine["coverage"] >= usual["coverage"] - 0.01
        MODEL_ERR = 5.0     # the energy model's own error on real flights is about 5 %
        reasons, cautions = [], []
        if rec == "standard":
            choice, headline = "usual", "Fly the usual route"
            reasons.append("The system found no route that is safe and uses less battery than the usual route on this field.")
        elif not safe:
            choice, headline = "usual", "Fly the usual route"
            reasons.append("The system's route did not pass the safety check (tree contact or missed ground).")
        elif sav >= MODEL_ERR:
            choice, headline = "system", "Fly the system's route"
            reasons.append(f"It uses {sav:.1f}% less battery ({wh:.0f} Wh, about {wh / area:.0f} Wh per hectare) with the same coverage.")
        elif sav >= 1.0:
            choice, headline = "either", "Either route is fine; the system's route saves a little"
            reasons.append(f"It saves {sav:.1f}% battery, which is within the energy model's own error of about {MODEL_ERR:.0f}%, so treat it as a small gain.")
        else:
            choice, headline = "usual", "Fly the usual route"
            reasons.append(f"The saving is only {sav:.1f}%, too small to be worth changing how the crew works.")
        if safe and rec != "standard":
            reasons.append(f"Tree contacts: {int(mine['contact_steps'])}; coverage {100 * mine['coverage']:.1f}% against {100 * usual['coverage']:.1f}% for the usual route.")
            if rec == "flatfirst":
                reasons.append("The route orders the strips of the field by how much battery each order costs, so steep ground is flown with a lighter tank where that saves energy.")
            elif rec == "agent":
                reasons.append("The trained agent chose lighter loads for the refills and a row direction that suits this slope. A lighter drone burns much less battery, because hover power grows with weight to the power 1.5.")
            else:
                reasons.append("The route uses the best row direction and shares the liquid evenly over the sorties, so the drone is lighter on average.")
        if d_sort > 0:
            cautions.append(f"It needs {d_sort} more take-off{'s' if d_sort > 1 else ''} ({int(mine['sorties'])} instead of {int(usual['sorties'])}) because the loads are smaller. Each take-off adds crew work and about 12% battery of fixed cost, which is already counted.")
        elif d_sort < 0:
            reasons.append(f"It needs {-d_sort} fewer take-off{'s' if d_sort < -1 else ''}.")
        if d_min > 1.0:
            cautions.append(f"It takes about {d_min:.0f} minutes longer ({mine['minutes']:.0f} against {usual['minutes']:.0f}). Choose the usual route if finishing fast matters more than battery.")
        elif d_min < -1.0:
            reasons.append(f"It also finishes about {-d_min:.0f} minutes sooner.")
        if choice == "system" and P.tank >= 25:
            reasons.append("With a large tank the usual route carries full, heavy loads, which is where the system saves the most.")
        if P.tank <= 15:
            cautions.append("With a small tank there is little to gain from lighter loads, so expect small savings.")
        cautions.append("These figures come from the energy model (about 5% error against real flight logs). The system's route has not been flown for real yet, so test it on a small block first.")
        return dict(choice=choice, headline=headline, recommended_id=rec, usual_id="standard", saving_pct=float(sav), wh_saved=float(wh),
                    wh_per_ha=float(wh / area), extra_sorties=d_sort, extra_minutes=d_min, reasons=reasons, cautions=cautions)

    def plan(self, req, progress=None, keep=None):
        t0 = time.time()
        P = self.problem(req)
        say = progress or (lambda *_: None)
        # ---- the three strategies
        say("Standard route")
        th_std = longest_edge_deg(P.poly)
        try:
            f0, d0, S0, fr0, fl0 = self._best(P, th_std, "trim", True)
            mstd, Sstd, _ = self._pack(P, "Standard route", th_std, f0, d0, "trim", True)
        except RuntimeError as e:
            raise RuntimeError("The drone cannot finish this field from the refill point you chose (" + str(e) + "). "
                               "Move the refill point closer to the field, or check the tank size and the battery reserve.")
        say("Fixed route without avoidance")
        try:                                           # the unsafe reference route is optional: skip it if it cannot be flown
            f1, d1, S1, fr1, fl1 = self._best(P, th_std, "trim", False)
            mfix, Sfix, _ = self._pack(P, "Fixed route (no avoidance)", th_std, f1, d1, "trim", False)
        except RuntimeError:
            mfix = Sfix = f1 = d1 = None

        say("Searching row direction")
        thetas = sorted(set([float(t) for t in range(0, 180, 15)] + [th_std, (th_std + 90.0) % 180.0]))
        res = {}
        for th in thetas:
            try:
                f_, d_, S_, fr_, fl_ = self._best(P, float(th), True, True)
            except RuntimeError:                       # this row direction cannot be flown from this refill point: skip it
                continue
            res[th] = (sum(S_["sortie_e"].values()) + 1000.0 * S_["contact"], f_, d_)
        if res:
            th_best = min(res, key=lambda t: res[t][0])
            for th in (th_best - 7.5, th_best + 7.5, th_best - 3.75, th_best + 3.75):
                th = float(th) % 180.0
                try:
                    f_, d_, S_, fr_, fl_ = self._best(P, th, True, True)
                except RuntimeError:
                    continue
                e = sum(S_["sortie_e"].values()) + 1000.0 * S_["contact"]
                if e < res[th_best][0] - 1e-9:
                    th_best = th
                    res[th] = (e, f_, d_)
        else:                                          # no searched direction worked: fall back to the standard route
            th_best = th_std
            res[th_std] = (sum(S0["sortie_e"].values()) + 1000.0 * S0["contact"], f0, d0)
        _, f2, d2 = res[th_best]
        fill2 = True
        e_std_tot = sum(S0["sortie_e"].values()) + 1000.0 * S0["contact"]
        if e_std_tot <= res[th_best][0] + 1e-9:          # never offer a plan worse than the standard one
            th_best, f2, d2, fill2 = th_std, f0, d0, "trim"
        mopt, Sopt, flopt = self._pack(P, "Optimised route", float(th_best), f2, d2, fill2, True)

        # ---- mass-aware path optimisation: strip order searched with the same energy model
        mff = Sff = None
        order_ff = None
        say("Mass-aware path optimisation")
        try:
            import flatfirst as FF
            ffr = FF.flat_first(P, float(th_best), (f2, d2), fill2)
            if ffr["e_best"] < ffr["e_ref"] - 1e-9:
                order_ff = [int(j) for j in ffr["order"]]
            mff, Sff, _ = self._pack(P, "Mass-aware path optimisation", float(th_best), f2, d2, fill2, True, order=order_ff)
            mff["strip_order_changed"] = order_ff is not None
        except Exception:
            mff = None

        # ---- lever tests, each against the standard route
        levers = []
        e_std = mstd["energy_pct"]

        def lever(label, m):
            levers.append(dict(label=label, energy_pct=m["energy_pct"], vs_standard_pct=(1 - m["energy_pct"] / e_std) * 100,
                               sorties=m["sorties"], coverage=m["coverage"], contact=m["contact_steps"]))
        lever("Standard route (rows along the longest edge, full tanks, last one trimmed)", mstd)
        say("Lever tests")
        try:
            f_, d_, S_, fr_, fl_ = self._best(P, float(th_best), "trim", True)
            mA, _, _ = self._pack(P, "angle only", float(th_best), f_, d_, "trim", True, record=False)
            lever(f"Best row direction only ({th_best:.0f} deg instead of {th_std:.0f})", mA)
        except RuntimeError:
            pass
        try:
            f_, d_, S_, fr_, fl_ = self._best(P, th_std, True, True)
            mB, _, _ = self._pack(P, "fill only", th_std, f_, d_, True, True, record=False)
            lever("Load-levelled refills only (split the liquid evenly over the sorties)", mB)
        except RuntimeError:
            pass
        lever("All levers together (the optimised route)", mopt)
        try:
            f_, d_, S_, fr_, fl_ = self._best(P, th_std, False, True)
            mF, _, _ = self._pack(P, "full tanks", th_std, f_, d_, False, True, record=False)
            lever("Reference: a full tank at every refill, nothing trimmed", mF)
        except RuntimeError:
            pass

        # ---- refill-point advisor
        say("Refill point advisor")
        try:
            advice = self.depot_advice(P, float(th_best), f2, d2, mopt["energy_pct"])
        except Exception:
            advice = None

        # ---- speed what-if
        say("Speed what-if")
        try:
            speeds = self.speed_curve(req, float(th_best), f2, d2)
        except Exception:
            speeds = []

        res_strats = []
        for m, S, key, desc in (
            (mfix, Sfix, "fixed", "Plain waypoint rows along the longest edge, no tree avoidance. The safety reference."),
            (mstd, Sstd, "standard", "Rows along the longest edge, tree arcs, full tanks with the last one trimmed. The fair baseline."),
            (mopt, Sopt, "optimised", "Searched row direction and start, load-levelled refills, tree arcs."),
        ):
            if m is None:
                continue
            res_strats.append(dict(id=key, name=m["name"], description=desc, metrics=_clean(m), route=_route(S)))
        if mff is not None:
            res_strats.append(dict(id="flatfirst", name=mff["name"], metrics=_clean(mff), route=_route(Sff),
                                   description="The strips of the field are put in the order that costs the least battery (steep ground with a lighter tank where it helps), searched with the energy model."))
        # ---- the AI agent route: the trained agent decides row direction, sweep and every refill load
        agent_out, agent_keep = None, None
        if req.get("agent_model"):
            say("AI agent route")
            try:
                import agent_route as AR
                dec = AR.decide(req["agent_model"], P)
                it = iter(dec["fills"])

                def cb(info, _it=it):
                    try:
                        return next(_it)
                    except StopIteration:        # not expected: the replay is deterministic
                        k = max(1, int(math.ceil(info["need"] / P.tank - 1e-9)))
                        return min(P.tank, info["need"] / k + 0.2)
                mag, Sag, _ = self._pack(P, "AI agent route", dec["theta"], dec["flip_rows"], dec["flip_dir"], cb, True)
                mag["exact_fill"] = "agent"
                res_strats.append(dict(id="agent", name="AI agent route", metrics=_clean(mag), route=_route(Sag),
                                       description="A trained deep-RL agent chose the row direction, the sweep and how much liquid to load at every refill.",
                                       decisions=dict(theta=dec["theta"], flip_rows=dec["flip_rows"], flip_dir=dec["flip_dir"],
                                                      loads_l=[round(x, 1) for x in dec["fills"]], model=req["agent_model"])))
                agent_keep = dict(P=P, theta=dec["theta"], flips=(dec["flip_rows"], dec["flip_dir"]), exact=True, avoid=True)
            except Exception as ex_:                # the plan still works without the agent
                agent_out = dict(error=str(ex_))
        if keep is not None:
            for key, th_, fl_, ex_, av_ in ((("fixed", th_std, (f1, d1), "trim", False),) if mfix is not None else ()) + \
                                           (("standard", th_std, (f0, d0), "trim", True),
                                            ("optimised", float(th_best), (f2, d2), fill2, True)) + \
                    ((("agent",) + (agent_keep["theta"], agent_keep["flips"], True, True),) if agent_keep else ()):
                keep[key] = dict(P=P, theta=th_, flips=fl_, exact=ex_, avoid=av_,
                                 route=next(s_ for s_ in res_strats if s_["id"] == key)["route"],
                                 metrics=next(s_ for s_ in res_strats if s_["id"] == key)["metrics"])
        if keep is not None and mff is not None:
            keep["flatfirst"] = dict(P=P, theta=float(th_best), flips=(f2, d2), exact=fill2, avoid=True, order=order_ff,
                                     route=next(s_ for s_ in res_strats if s_["id"] == "flatfirst")["route"],
                                     metrics=next(s_ for s_ in res_strats if s_["id"] == "flatfirst")["metrics"])
        cov_std = next(s["metrics"]["coverage"] for s in res_strats if s["id"] == "standard")
        ok = [s for s in res_strats if s["metrics"]["contact_steps"] == 0 and s["metrics"]["coverage"] >= max(0.90, cov_std - 0.01)]
        rec = min(ok, key=lambda s: s["metrics"]["energy_pct"])["id"] if ok else "standard"
        # one system: the agent's route is the route unless the safety check fails (tree contact, missed ground, or worse than the standard route)
        ag = next((s for s in res_strats if s["id"] == "agent"), None)
        if ag is not None:
            e_std_ = next(s["metrics"]["energy_pct"] for s in res_strats if s["id"] == "standard")
            good = ag in ok and ag["metrics"]["energy_pct"] <= e_std_
            agent_out = dict(used=bool(good), model=ag["decisions"]["model"], decisions=ag["decisions"],
                             vs_standard_pct=float((1 - ag["metrics"]["energy_pct"] / e_std_) * 100),
                             note="" if good else "Safety check: the agent's route was not used because it touches a tree, misses ground, or uses more battery than the standard route.")
            if good:
                rec = "agent"
        route_advice = self._route_advice(res_strats, rec, P, float(self.model.battery_wh))
        slope_load = self._slope_load(res_strats, P)
        out = dict(
            site=req["site"], polygon=np.asarray(P.poly).tolist(), trees=[dict(x=float(a), y=float(b), r=float(r))
                                                                       for (a, b), r in zip(P.trees, P.rad)],
            depot=P.depot.tolist(), params=P.par, z_scale=float(req.get("z_scale", 1.0)),
            field_ha=poly_area(P.poly) / 1e4, strategies=res_strats, recommended=rec, levers=levers,
            depot_advice=advice, speed_curve=speeds, assumptions=ASSUMPTIONS, battery_wh=float(self.model.battery_wh),
            seconds=time.time() - t0, theta=float(th_best), agent=agent_out, route_advice=route_advice, slope_load=slope_load)
        return out

    # ---------------------------------------------------------------- live re-planning
    def route_coverage(self, P, route):
        """coverage of the polygon from the recorded route (world frame): spray steps swept at 1 m"""
        x, y, kd = np.asarray(route["x"]), np.asarray(route["y"]), np.asarray(route["kind"])
        m = kd[1:] == 1
        seg = np.stack([x[:-1], y[:-1], x[1:], y[1:]], 1)[m]
        lo, hi = P.poly.min(0), P.poly.max(0)
        cx = np.arange(lo[0] + COV_DX / 2, hi[0], COV_DX)
        cy = np.arange(lo[1] + COV_DX / 2, hi[1], COV_DX)
        gx, gy = np.meshgrid(cx, cy, indexing="ij")
        cells = np.stack([gx.ravel(), gy.ravel()], 1)
        ok = point_in_poly(cells[:, 0], cells[:, 1], P.poly)
        if len(P.trees):
            d = np.hypot(cells[:, None, 0] - P.trees[None, :, 0], cells[:, None, 1] - P.trees[None, :, 1])
            ok &= ~(d < P.rad[None, :]).any(1)
        if len(seg) == 0:
            return 0.0
        L = np.hypot(seg[:, 2] - seg[:, 0], seg[:, 3] - seg[:, 1])
        ns = np.maximum(1, np.ceil(L).astype(int))
        idx = np.repeat(np.arange(len(seg)), ns)
        j = np.arange(len(idx)) - np.repeat(np.cumsum(ns) - ns, ns)
        f = ((j + 0.5) / ns[idx])[:, None]
        pts = seg[idx, :2] * (1 - f) + seg[idx, 2:] * f
        dist, _ = cKDTree(pts).query(cells, distance_upper_bound=P.swath / 2)
        cov = np.isfinite(dist)
        return float((cov & ok).sum() / max(int(ok.sum()), 1))

    def replan(self, info, i, tree):
        """A new obstacle appears while the drone is at route step i: keep what is flown, re-plan the rest."""
        P0, route = info["P"], info["route"]
        i = int(max(0, min(i, len(route["x"]) - 1)))
        trees = [dict(x=float(a), y=float(b), r=float(r)) for (a, b), r in zip(P0.trees, P0.rad)] + [tree]
        P2 = Problem(P0.z, P0.poly, trees, P0.depot, P0.par, P0.model)
        fr0, fr2 = Frame(P0, info["theta"]), Frame(P2, info["theta"])
        f_, d_ = info["flips"]
        path0 = fr0.build(f_, d_, info["avoid"], order=info.get("order"))
        path2 = fr2.build(f_, d_, info["avoid"], order=info.get("order"))
        x0, y0, v0, sp0, rid0 = path0
        x2, y2, v2, sp2, rid2 = path2
        p_old = int(min(route["pidx"][i], len(rid0) - 1))
        r = int(rid0[p_old])
        wpos = np.array([route["x"][i], route["y"][i]])
        lpos = rot(wpos - P0.centre, -math.radians(info["theta"]))
        # direction of travel along the current row (from the old path)
        j0 = p_old
        while j0 < len(sp0) - 1 and not sp0[j0]:
            j0 += 1
        dirn = 1.0 if x0[min(j0 + 1, len(x0) - 1)] >= x0[j0] else -1.0
        cand = np.where((rid2 == r) & sp2 & ((x2[:-1] - lpos[0]) * dirn >= -0.5))[0]
        if len(cand):
            j = int(cand[0])
        else:
            later = np.where(rid2 > r)[0]
            j = int(later[0]) if len(later) else len(x2) - 1
        t_now = route["t"][i]
        state = dict(pos=lpos.copy(), bat=float(route["bat"][i]), liq=float(route["liq"][i]), sortie=int(route["sortie"][i]),
                     sortie_e={int(route["sortie"][i]): 0.0}, t=float(t_now), idx=j, fresh=False)
        fl = Flight(fr2)
        S = fl.run(path2, info["exact"], state=state, record=True)
        new = _route(S)
        # merge: flown part + new part (the new part starts at the drone's current position)
        merged = {}
        for k in ("x", "y", "alt", "liq", "bat", "kind", "sortie", "t", "pidx"):
            head = list(route[k][:i + 1])
            tail = list(new[k][1:]) if len(new[k]) else []
            merged[k] = head + tail
        merged["refills"] = [rf for rf in route["refills"] if rf["t"] <= t_now] + new["refills"]
        bat = np.asarray(merged["bat"])
        energy = float(np.maximum(0.0, -np.diff(bat)).sum())
        e_before = float(np.maximum(0.0, -np.diff(np.asarray(route["bat"])))[: max(i, 0)].sum())
        e_orig = float(np.maximum(0.0, -np.diff(np.asarray(route["bat"]))).sum())
        # gap to the NEW tree on the new part, and to all trees on the new part
        newx, newy = np.asarray(new["x"]), np.asarray(new["y"])
        if len(newx):
            allt = P2.trees
            g = (np.hypot(newx[:, None] - allt[None, :, 0], newy[:, None] - allt[None, :, 1]) - P2.rad[None, :]).min(1)
            min_gap, contacts = float(g.min()), int((g < COLLIDE_M).sum())
        else:
            min_gap, contacts = 99.0, 0
        cov = self.route_coverage(P2, merged)
        sorties = int(max(merged["sortie"]))
        m = dict(energy_pct=energy, energy_before_pct=e_before, original_energy_pct=e_orig,
                 extra_energy_pct=energy - e_orig, coverage=cov, sorties=sorties, contact_steps=contacts, min_gap_m=min_gap,
                 minutes=merged["t"][-1] / 60.0, litres=float(S["litres"]), replanned_from_step=i)
        info2 = dict(info, P=P2, route=merged, metrics=m)
        return info2, merged, _clean(m)

    def depot_advice(self, P, theta, fr_, fd, e_ref):
        fr = Frame(P, theta)
        c = P.centre
        cands = []
        poly = P.poly
        n = len(poly)
        for i in range(n):
            mid = (poly[i] + poly[(i + 1) % n]) / 2
            out_dir = mid - c
            out_dir /= max(np.hypot(*out_dir), 1e-6)
            cands.append(mid + out_dir * 6.0)
            cands.append(poly[i] + (poly[i] - c) / max(np.hypot(*(poly[i] - c)), 1e-6) * 6.0)
        lim = P.z.shape[0] * GRID - 3
        cands = [np.clip(p, 3, lim) for p in cands]
        results = []
        for p in cands:
            P2 = Problem(P.z, P.poly, [dict(x=a, y=b, r=r) for (a, b), r in zip(P.trees, P.rad)], p, P.par, P.model)
            fr2 = Frame(P2, theta)
            try:
                S = Flight(fr2).run(fr2.build(fr_, fd, True), True)
            except RuntimeError:
                continue
            if S["contact"] == 0:
                results.append((sum(S["sortie_e"].values()), p, S["sortie"]))
        if not results:
            return None
        e, p, k = min(results, key=lambda r: r[0])
        return dict(x=float(p[0]), y=float(p[1]), energy_pct=float(e), saving_pct=float((1 - e / e_ref) * 100),
                    sorties=int(k), tried=len(results))

    def speed_curve(self, req, theta, fr_, fd):
        out = []
        for kmh in (3.0, 4.5, 6.4, 9.0, 12.0, 15.0, 18.0):
            r2 = dict(req)
            r2["params"] = dict(req.get("params") or {}, spray_kmh=kmh)
            P = self.problem(r2)
            fr = Frame(P, theta)
            fl = Flight(fr)
            try:
                S = fl.run(fr.build(fr_, fd, True), True)
            except RuntimeError:                       # this speed cannot be flown here: leave it out of the chart
                continue
            m = fl.metrics(S)
            out.append(dict(kmh=kmh, energy_pct=m["energy_pct"], sorties=m["sorties"], minutes=m["minutes"],
                            coverage=m["coverage"]))
        return out


def _clean(m):
    return {k: (float(v) if isinstance(v, (np.floating, float)) else (int(v) if isinstance(v, (np.integer,)) else v))
            for k, v in m.items()}


def _route(S):
    """compact per-step arrays for the viewer (world frame)"""
    xs, ys, al, lq, bt, kd, ss, tt, pi = [], [], [], [], [], [], [], [], []
    for r in S["rec"]:
        sl = slice(1, None) if xs else slice(0, None)
        xs += np.round(r["x"][sl], 2).tolist(); ys += np.round(r["y"][sl], 2).tolist()
        al += np.round(r["alt"][sl], 2).tolist(); lq += np.round(r["liq"][sl], 3).tolist()
        bt += np.round(r["bat"][sl], 3).tolist(); kd += [int(k) for k in r["kind"][sl]]
        ss += [r["sortie"]] * len(r["x"][sl]); tt += np.round(r["t"][sl], 2).tolist()
        pi += [int(p) for p in r["pidx"][sl]]
    return dict(x=xs, y=ys, alt=al, liq=lq, bat=bt, kind=kd, sortie=ss, t=tt, pidx=pi, refills=S["refills"])


def example_request(site, z_scale=1.0, size=300.0):
    """a ready-made demo field: a 130 x 110 m block with a notch and 10 trees (centred in the site)"""
    rng = np.random.default_rng(11)
    sh = (size - 300.0) / 2.0
    poly = [[40, 40], [175, 48], [185, 130], [120, 160], [55, 150]]
    trees = []
    while len(trees) < 10:
        p = rng.uniform([50, 55], [175, 145])
        if point_in_poly(np.array([p[0]]), np.array([p[1]]), np.array([[40, 40], [175, 48], [185, 130], [120, 160], [55, 150]]))[0] and all(
                math.hypot(p[0] - t["x"], p[1] - t["y"]) > 14 for t in trees):
            trees.append(dict(x=float(p[0]), y=float(p[1]), r=float(rng.uniform(1.5, 3.0))))
    poly = [[p[0] + sh, p[1] + sh] for p in poly]
    trees = [dict(t, x=t["x"] + sh, y=t["y"] + sh) for t in trees]
    return dict(site=site, polygon=poly, trees=trees, depot=[25 + sh, 30 + sh], params={}, z_scale=z_scale)


if __name__ == "__main__":
    mp = MissionPlanner()
    print(json.dumps(mp.sites.listing(), indent=1))
    req = example_request(mp.sites.defs[1]["id"])
    t = time.time()
    r = mp.plan(req, progress=print)
    print(f"planned in {time.time() - t:.1f} s, theta {r['theta']}")
    for s in r["strategies"]:
        m = s["metrics"]
        print(f"{s['name']:30s} energy {m['energy_pct']:6.1f}%  sorties {m['sorties']}  cover {100 * m['coverage']:.1f}%  "
              f"contacts {m['contact_steps']}  min gap {m['min_gap_m']:.1f}  min {m['minutes']:.1f}  transit {m['e_transit']:.1f}  turn {m['e_turn']:.1f}")
    for l in r["levers"]:
        print(f"  {l['label']:70s} {l['energy_pct']:6.1f}  {l['vs_standard_pct']:+.1f}%  cov {100 * l['coverage']:.1f}")
    print("depot advice", r["depot_advice"])
    for s in r["speed_curve"]:
        print("  speed", s)
