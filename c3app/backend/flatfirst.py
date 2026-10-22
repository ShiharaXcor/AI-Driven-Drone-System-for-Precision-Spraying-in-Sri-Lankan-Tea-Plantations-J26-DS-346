"""Flat-first ordering test: spray the flat strips of the field while the tank is heavy and the steep strips when it is light.

The rows of the field are grouped into strips ("chunks", about a third of a tank each). We try three orders and keep the cheapest:
  1. the best order of the search planner (rows in sequence, best direction)       <- the reference
  2. 'flat first' rule: strips sorted from the flattest to the steepest
  3. a short search: swap strips, reverse strips, reverse the whole order, keep any change that costs less battery
Everything is scored with the same energy model, tree safety and coverage rules as the other routes. Nothing here assumes the idea helps."""
import math
import numpy as np
from scipy.ndimage import map_coordinates
from engine import Frame, Flight, GRID, COLLIDE_M


def row_slopes(P, fr):
    """mean ground slope (degrees) under each row"""
    gx, gy = np.gradient(P.z, GRID)
    slope = np.degrees(np.arctan(np.hypot(gx, gy)))
    out = []
    for yc, ivs in fr.rows():
        xs = np.concatenate([np.linspace(a, b, max(2, int((b - a) / 5))) for a, b in ivs])
        wx, wy = fr.to_world(xs, np.full_like(xs, yc))
        out.append(float(map_coordinates(slope, [wx / GRID - 0.5, wy / GRID - 0.5], order=1, mode="nearest").mean()))
    return np.array(out)


def make_chunks(nrows, per):
    return [list(range(i, min(i + per, nrows))) for i in range(0, nrows, per)]


def order_of(chunks, perm, rev):
    out = []
    for k in perm:
        c = chunks[k]
        out += c[::-1] if rev[k] else c
    return out


def energy(fl, fr, flips, order, exact):
    path = fr.build(flips[0], flips[1], True, order=order)
    try:
        S = fl.run(path, exact)
    except RuntimeError:
        return 1e9, None
    return sum(S["sortie_e"].values()) + 1000.0 * S["contact"], S


def flat_first(P, theta, flips, exact=True, iters=60, seed=0):
    """returns dict(order, e_ref, e_rule, e_best, which) for the Frame at angle theta"""
    fr = Frame(P, float(theta)); fl = Flight(fr)
    nrows = len(fr.rows())
    e_ref, S_ref = energy(fl, fr, flips, list(range(nrows)) if not flips[0] else list(range(nrows))[::-1], exact)
    base = list(range(nrows))[::-1] if flips[0] else list(range(nrows))
    # strip size: about a third of the liquid one tank carries, in rows
    row_len = np.mean([sum(b - a for a, b in ivs) for _, ivs in fr.rows()])
    rows_per_tank = max(1.0, P.tank / max(P.l_per_m * row_len, 1e-6))
    per = int(max(2, round(rows_per_tank / 3)))
    chunks = make_chunks(nrows, per)
    # chunks follow the base order of the rows
    chunks = [[base[j] for j in c] for c in make_chunks(nrows, per)]
    sl = row_slopes(P, fr)
    cs = np.array([sl[c].mean() for c in chunks])
    K = len(chunks)
    rev0 = [False] * K
    cand = {"reference": (list(range(K)), rev0)}
    cand["flat first (rule)"] = (list(np.argsort(cs, kind="stable")), rev0)
    cand["steep first (rule)"] = (list(np.argsort(-cs, kind="stable")), rev0)
    best_name, best_e, best_ord, best_S = "reference", e_ref, base, S_ref
    scores = {}
    for name, (perm, rev) in cand.items():
        o = order_of(chunks, perm, rev)
        e, S = energy(fl, fr, flips, o, exact)
        scores[name] = e
        if e < best_e - 1e-9:
            best_name, best_e, best_ord, best_S = name, e, o, S
    # short search starting from the best so far
    rng = np.random.default_rng(seed)
    perm = list(cand[best_name][0]) if best_name != "reference" else list(range(K)); rev = list(cand[best_name][1]) if best_name != "reference" else rev0[:]
    cur = best_e
    for _ in range(iters):
        p2, r2 = perm[:], rev[:]
        mv = rng.integers(0, 3)
        if mv == 0 and K > 1:
            i, j = rng.choice(K, 2, replace=False); p2[i], p2[j] = p2[j], p2[i]
        elif mv == 1:
            k = int(rng.integers(0, K)); r2[k] = not r2[k]
        else:
            i, j = sorted(rng.choice(K, 2, replace=False)); p2[i:j + 1] = p2[i:j + 1][::-1]
        o = order_of(chunks, p2, r2)
        e, S = energy(fl, fr, flips, o, exact)
        if e < cur - 1e-9:
            perm, rev, cur = p2, r2, e
            if e < best_e - 1e-9:
                best_name, best_e, best_ord, best_S = "searched order", e, o, S
    scores["searched order"] = cur
    return dict(order=best_ord, e_ref=e_ref, e_best=best_e, which=best_name, scores=scores, chunk_slopes=cs.tolist(), n_chunks=K)
