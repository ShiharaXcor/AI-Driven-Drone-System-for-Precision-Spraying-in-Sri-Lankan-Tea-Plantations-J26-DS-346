"""Random tea fields for training and testing the route agent.

A field = terrain window (300 x 300 m at 5 m) + polygon + trees + refill point + drone settings.
Terrain comes from an elevation tile (the real SRTM tile on the user's machine). Extra roughness and
steepness can be added to test on steeper ground than the smooth 90 m data shows.
"""
import math
import numpy as np
from scipy.ndimage import map_coordinates, gaussian_filter

GRID, SRTM_DX, SIZE = 5.0, 92.77, 300.0
N = int(SIZE / GRID)


def terrain_window(z_tile, rng, z_scale=1.0, rough_m=0.0, rough_len=25.0, cols=(0.0, 1.0)):
    """cut a random 300 m window from the tile (cubic interpolation to 5 m), then optionally steepen
    (z_scale around the window mean) and add fine roughness (std rough_m metres, correlation length rough_len m)"""
    R, C = z_tile.shape
    w = int(math.ceil(SIZE / SRTM_DX)) + 1
    clo, chi = int(cols[0] * (C - w)), max(int(cols[1] * (C - w)), int(cols[0] * (C - w)) + 1)
    r0, c0 = rng.integers(0, R - w), rng.integers(clo, chi)
    win = z_tile[r0:r0 + w, c0:c0 + w]
    # random flip / transpose so the same tile gives different slope directions
    if rng.random() < .5: win = win[::-1]
    if rng.random() < .5: win = win[:, ::-1]
    if rng.random() < .5: win = win.T
    pos = (np.arange(N) + .5) * GRID / SRTM_DX
    ii, jj = np.meshgrid(pos, pos, indexing="ij")
    z = map_coordinates(win, [ii, jj], order=3, mode="nearest")
    z = z.mean() + (z - z.mean()) * z_scale
    if rough_m > 0:
        n = gaussian_filter(rng.standard_normal((N, N)), rough_len / GRID)
        z = z + n / max(n.std(), 1e-9) * rough_m
    return z


def random_polygon(rng, area_ha=(0.6, 3.0)):
    """a convex-ish polygon of 4-7 vertices inside the window"""
    for _ in range(200):
        k = int(rng.integers(4, 8))
        target = rng.uniform(*area_ha) * 1e4
        ang = np.sort(rng.uniform(0, 2 * np.pi, k))
        rad = rng.uniform(.65, 1.0, k)
        aspect = rng.uniform(.45, 1.0)
        p = np.stack([np.cos(ang) * rad, np.sin(ang) * rad * aspect], 1)
        a = .5 * abs(np.dot(p[:, 0], np.roll(p[:, 1], -1)) - np.dot(p[:, 1], np.roll(p[:, 0], -1)))
        if a < 1e-3:
            continue
        p *= math.sqrt(target / a)
        th = rng.uniform(0, np.pi)
        c, s = math.cos(th), math.sin(th)
        p = p @ np.array([[c, -s], [s, c]]).T
        lo, hi = p.min(0), p.max(0)
        if (hi - lo).max() > SIZE - 40:
            continue
        p = p - (lo + hi) / 2 + SIZE / 2 + rng.uniform(-10, 10, 2)
        return p
    raise RuntimeError("could not draw a polygon")


def in_poly(p, poly):
    x, y = p
    inside = False
    n = len(poly)
    for i in range(n):
        (ax, ay), (bx, by) = poly[i], poly[(i + 1) % n]
        if (ay > y) != (by > y) and x < ax + (bx - ax) * (y - ay) / (by - ay):
            inside = not inside
    return inside


def random_trees(rng, poly, n):
    lo, hi = poly.min(0), poly.max(0)
    out = []
    tries = 0
    while len(out) < n and tries < 4000:
        tries += 1
        p = rng.uniform(lo, hi)
        if in_poly(p, poly) and all(math.hypot(p[0] - t["x"], p[1] - t["y"]) > 12 for t in out):
            out.append(dict(x=float(p[0]), y=float(p[1]), r=float(rng.uniform(1.5, 3.2))))
    return out


def random_depot(rng, poly):
    """refill point just outside the polygon, near a random vertex"""
    c = poly.mean(0)
    v = poly[rng.integers(len(poly))]
    d = v - c
    d /= max(np.hypot(*d), 1e-6)
    return np.clip(v + d * rng.uniform(4, 14), 4, SIZE - 4)


def random_field(z_tile, rng, tank=None, trees=None, z_scale=None, rough_m=None, area_ha=(0.6, 3.0), cols=(0.0, 1.0)):
    """one random problem description (a dict the planner and the agent both read)"""
    zs = rng.uniform(.8, 1.3) if z_scale is None else z_scale
    rm = rng.choice([0.0, 0.0, 1.0, 2.0]) if rough_m is None else rough_m
    z = terrain_window(z_tile, rng, zs, rm, cols=cols)
    poly = random_polygon(rng, area_ha)
    nt = int(rng.integers(0, 16)) if trees is None else trees
    t = random_trees(rng, poly, nt)
    tank_l = float(rng.choice([15., 20., 20., 20., 25., 30., 40.])) if tank is None else float(tank)
    return dict(z=z, poly=poly, trees=t, depot=random_depot(rng, poly), tank_l=tank_l, z_scale=zs, rough_m=float(rm))
