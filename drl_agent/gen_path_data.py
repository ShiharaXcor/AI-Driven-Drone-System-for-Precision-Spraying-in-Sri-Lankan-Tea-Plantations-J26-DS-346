# gen_path_data.py
# Component 3 - SYNTHETIC input data for the energy-aware path advisor.
#
# Run (from ~/component3, venv active):   python3 drl_agent/gen_path_data.py --fields 100
#
# Creates  data/path_advisor/ :
#   fields.json      field polygons (rect / L-shape / blob), base point, trees, terrain info, train/val/test split
#   terrain.npz      40x40 height grid (5 m) for each field, cut from the REAL SRTM tile with the simulator's own code
#   user_paths.json  5 "pilot-style" planned paths per field (waypoints + spray flag + quality metrics)
#   manifest.json    settings, seeds, data dictionary, what is synthetic and what is real
#   preview.png      12 example fields with trees and a planned path
#
# EVERYTHING HERE IS SYNTHETIC INPUT DATA (shapes, trees, planned paths). The terrain heights are real SRTM.
# It contains NO measured battery data, so it can never be used to claim the energy model is accurate.

import os, sys, json, argparse
import numpy as np
from matplotlib.path import Path as MPath
from scipy.spatial import cKDTree

BASE = os.environ.get("C3_BASE", os.path.expanduser("~/component3"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tea_spray_env as E
from tea_spray_env import TeaSprayEnv, PATCH_M, SWATH_M

LO, HI = 8.0, PATCH_M - 8.0            # fields stay inside the 200 m patch (base at (5,5) is outside)
BASE_XY = (5.0, 5.0)


# ---------------------------------------------------------------- field shapes
def shoelace(p):
    x, y = p[:, 0], p[:, 1]
    return 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def raw_shape(rng, kind):
    if kind == "rect":
        asp = rng.uniform(1.0, 2.5)
        return np.array([[0, 0], [asp, 0], [asp, 1], [0, 1]], float)
    if kind == "L":
        c = rng.uniform(0.35, 0.5)
        asp = rng.uniform(1.0, 2.0)
        return np.array([[0, 0], [asp, 0], [asp, 1 - c], [asp * (1 - c), 1 - c], [asp * (1 - c), 1], [0, 1]], float)
    k = int(rng.integers(8, 13))                      # blob: star-shaped, always a simple polygon
    ang = np.linspace(0, 2 * np.pi, k, endpoint=False) + rng.uniform(-0.2, 0.2, k)
    r = 1 + rng.uniform(-0.3, 0.3, k)
    pts = np.stack([r * np.cos(ang) * rng.uniform(1.0, 2.0), r * np.sin(ang)], 1)
    return pts


def make_field(rng, kind, target_ha):
    for _ in range(200):
        p = raw_shape(rng, kind)
        p = p * np.sqrt(target_ha * 1e4 / shoelace(p))
        t = rng.uniform(0, 2 * np.pi)
        R = np.array([[np.cos(t), -np.sin(t)], [np.sin(t), np.cos(t)]])
        p = p @ R.T
        p -= p.min(0)
        w, h = p.max(0)
        if w > HI - LO or h > HI - LO:
            continue
        p += np.array([rng.uniform(LO, HI - w), rng.uniform(LO, HI - h)])
        return np.round(p, 1)
    raise RuntimeError("could not fit a field")


def sample_trees(rng, poly, mpath, n):
    pts, rad = [], []
    tries = 0
    while len(pts) < n and tries < 5000:
        tries += 1
        inside = rng.random() < 0.75
        q = rng.uniform(15, PATCH_M - 15, 2)
        if inside != bool(mpath.contains_point(q)):
            continue
        if np.hypot(q[0] - BASE_XY[0], q[1] - BASE_XY[1]) < 12:
            continue
        if any(np.hypot(*(q - p)) < 8 for p in pts):
            continue
        pts.append(q)
        rad.append(rng.uniform(1.5, 3.0))
    return np.round(np.array(pts).reshape(-1, 2), 1), np.round(np.array(rad), 2)


# ---------------------------------------------------------------- planned paths
def sweep(poly, mpath, heading_deg, spacing):
    th = np.radians(heading_deg)
    u, v = np.array([np.cos(th), np.sin(th)]), np.array([-np.sin(th), np.cos(th)])
    A = poly @ u
    Bc = poly @ v
    offs = np.arange(Bc.min() + spacing / 2, Bc.max(), spacing)
    segs, d = [], 1
    for b in offs:
        a = np.arange(A.min(), A.max() + 1, 1.0)
        xy = a[:, None] * u + b * v
        ins = mpath.contains_points(xy)
        runs, i = [], 0
        while i < len(ins):
            if ins[i]:
                j = i
                while j + 1 < len(ins) and ins[j + 1]:
                    j += 1
                runs.append((xy[i], xy[j]))
                i = j + 1
            else:
                i += 1
        if d == -1:
            runs = [(e, s) for s, e in runs[::-1]]
        segs += runs
        d *= -1
    wp = [[BASE_XY[0], BASE_XY[1], 0]]
    for s, e in segs:
        wp.append([float(s[0]), float(s[1]), 0])      # transit leg to the start of the row
        wp.append([float(e[0]), float(e[1]), 1])      # spraying leg along the row
    wp.append([BASE_XY[0], BASE_XY[1], 0])
    return np.round(np.array(wp), 1)


def principal_heading(poly):
    c = poly - poly.mean(0)
    w, V = np.linalg.eigh(np.cov(c.T))
    ax = V[:, np.argmax(w)]
    return float(np.degrees(np.arctan2(ax[1], ax[0])) % 180)


def path_metrics(wp, poly, mpath, trees, rad):
    legs = [(wp[i - 1, :2], wp[i, :2], wp[i, 2]) for i in range(1, len(wp))]
    length = sum(np.hypot(*(b - a)) for a, b, s in legs)
    spray = sum(np.hypot(*(b - a)) for a, b, s in legs if s)
    samp, sp_samp = [], []
    for a, b, s in legs:
        n = max(2, int(np.hypot(*(b - a))))
        q = a + (b - a) * np.linspace(0, 1, n)[:, None]
        samp.append(q)
        if s:
            sp_samp.append(q)
    samp = np.vstack(samp)
    sp = np.vstack(sp_samp) if sp_samp else np.zeros((1, 2)) - 999
    g = np.arange(1.0, PATCH_M, 2.0)
    gx, gy = np.meshgrid(g, g, indexing="ij")
    cells = np.stack([gx.ravel(), gy.ravel()], 1)
    cells = cells[mpath.contains_points(cells)]
    cov = float((cKDTree(sp).query(cells)[0] <= SWATH_M / 2).mean() * 100)
    hit = 0
    if len(trees):
        dmin = (cKDTree(trees).query(samp)[0] if len(trees) > 0 else np.inf)
        hit = int(np.sum(np.hypot(*(samp[:, None, :] - trees[None, :, :]).transpose(2, 0, 1)) <
                         (rad + E.COLLIDE_M)[None, :]))
    liquid = spray * E.L_PER_M
    return dict(length_m=round(float(length), 1), spray_m=round(float(spray), 1),
                transit_m=round(float(length - spray), 1), coverage_pct=round(cov, 1),
                liquid_L=round(float(liquid), 2), sorties=int(np.ceil(liquid / E.LIQUID_L)),
                tree_contact_samples=hit)


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fields", type=int, default=100)
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--out", default=f"{BASE}/data/path_advisor")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    rng = np.random.default_rng(a.seed)
    env = TeaSprayEnv()
    kinds = ["rect", "L", "blob"]
    dens = [0, 4, 8, 16]
    n = a.fields
    order = rng.permutation(n)
    split = np.empty(n, dtype=object)
    split[order[:int(.6 * n)]] = "train"
    split[order[int(.6 * n):int(.75 * n)]] = "val"
    split[order[int(.75 * n):]] = "test"

    fields, paths, terr = [], {}, {}
    for i in range(n):
        fid = f"F{i:03d}"
        kind = kinds[i % 3]
        poly = make_field(rng, kind, rng.uniform(0.2, 0.8))
        mp = MPath(np.vstack([poly, poly[:1]]))
        nt = dens[int(rng.integers(0, len(dens)))]
        trees, rad = sample_trees(rng, poly, mp, nt)
        env.reset(seed=9000 + i)                       # same terrain code as the simulator
        z = env.z.copy()
        gy, gx = np.gradient(z, E.TERRAIN_DX)
        sl = np.degrees(np.arctan(np.hypot(gx, gy)))
        c = (np.arange(env.n_t) + 0.5) * E.TERRAIN_DX
        cxg, cyg = np.meshgrid(c, c, indexing="ij")
        inside = mp.contains_points(np.stack([cxg.ravel(), cyg.ravel()], 1)).reshape(cxg.shape)
        fields.append(dict(id=fid, split=str(split[i]), kind=kind, synthetic=True,
                           area_ha=round(shoelace(poly) / 1e4, 3), polygon=poly.tolist(), base=list(BASE_XY),
                           trees=dict(n=int(len(trees)), xy=trees.tolist(), r=rad.tolist()),
                           terrain=dict(source="SRTM (real)", seed=9000 + i, window_rc=[int(v) for v in env._rc],
                                        mean_slope_deg=round(float(sl[inside].mean()), 1),
                                        relief_m=round(float(z[inside].max() - z[inside].min()), 1))))
        terr[fid] = z
        specs = [("sweep_x", 0.0, 6.0), ("sweep_y", 90.0, 6.0), ("sweep_long_axis", principal_heading(poly), 6.0),
                 ("sweep_random", float(rng.uniform(0, 180)), 6.0), ("sweep_overlap", float(rng.uniform(0, 180)), 4.5)]
        plist = []
        for nm, h, sp in specs:
            wp = sweep(poly, mp, h, sp)
            plist.append(dict(type=nm, heading_deg=round(h, 1), spacing_m=sp, waypoints=wp.tolist(),
                              metrics=path_metrics(wp, poly, mp, trees, rad)))
        paths[fid] = plist

    json.dump(fields, open(f"{a.out}/fields.json", "w"))
    np.savez_compressed(f"{a.out}/terrain.npz", **terr)
    json.dump(paths, open(f"{a.out}/user_paths.json", "w"))
    man = dict(generator="gen_path_data.py", seed=a.seed, n_fields=n, patch_m=PATCH_M, terrain_dx_m=E.TERRAIN_DX,
               srtm_cell_m=E.SRTM_DX, swath_m=SWATH_M, base_xy=BASE_XY,
               real_data=["terrain heights (SRTM 90 m, interpolated to 5 m)"],
               synthetic_data=["field polygons", "tree positions and radii", "pilot-style planned paths"],
               not_included=["measured battery or power data", "wind", "real pilot tracks", "real tree map", "real block shapes"],
               note="terrain windows can overlap between splits (the SRTM tile is small); splits differ in shape, trees and paths.")
    json.dump(man, open(f"{a.out}/manifest.json", "w"), indent=2)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(3, 4, figsize=(14, 10))
    for ax, f in zip(axs.ravel(), fields[:12]):
        z = terr[f["id"]]
        ax.imshow(z.T, origin="lower", extent=[0, PATCH_M, 0, PATCH_M], cmap="terrain", alpha=0.6)
        P = np.array(f["polygon"])
        ax.fill(P[:, 0], P[:, 1], fc="none", ec="k", lw=1.5)
        for (x, y), r in zip(f["trees"]["xy"], f["trees"]["r"]):
            ax.add_patch(plt.Circle((x, y), r, color="darkgreen"))
        pth = paths[f["id"]][3]
        w = np.array(pth["waypoints"])
        for k in range(1, len(w)):
            ax.plot(w[k - 1:k + 1, 0], w[k - 1:k + 1, 1], "-", color="red" if w[k, 2] else "gray", lw=0.8)
        ax.set_title(f"{f['id']} {f['kind']} {f['area_ha']} ha, {f['trees']['n']} trees", fontsize=9)
        ax.set_xticks([]); ax.set_yticks([])
    fig.suptitle("Synthetic fields on real terrain - red: spraying legs of a planned path, grey: transit", fontsize=12)
    fig.tight_layout()
    fig.savefig(f"{a.out}/preview.png", dpi=110)

    print(f"\nWrote {n} fields to {a.out}")
    print("splits:", {s: int(np.sum(split == s)) for s in ("train", "val", "test")},
          " kinds:", {k: sum(f['kind'] == k for f in fields) for k in kinds})
    ar = [f["area_ha"] for f in fields]
    sl = [f["terrain"]["mean_slope_deg"] for f in fields]
    print(f"area ha  : {min(ar):.2f} - {max(ar):.2f} (mean {np.mean(ar):.2f})")
    print(f"slope deg: {min(sl):.1f} - {max(sl):.1f} (mean {np.mean(sl):.1f})   trees: {dict(zip(*np.unique([f['trees']['n'] for f in fields], return_counts=True)))}")
    print(f"{'planned path type':18s} {'length m':>8s} {'spray m':>8s} {'coverage %':>10s} {'sorties':>8s} {'cross trees':>11s}")
    for nm in ("sweep_x", "sweep_y", "sweep_long_axis", "sweep_random", "sweep_overlap"):
        m = [p["metrics"] for f in paths.values() for p in f if p["type"] == nm]
        print(f"{nm:18s} {np.mean([x['length_m'] for x in m]):8.0f} {np.mean([x['spray_m'] for x in m]):8.0f} "
              f"{np.mean([x['coverage_pct'] for x in m]):10.1f} {np.mean([x['sorties'] for x in m]):8.2f} "
              f"{100 * np.mean([x['tree_contact_samples'] > 0 for x in m]):10.0f}%")


if __name__ == "__main__":
    main()