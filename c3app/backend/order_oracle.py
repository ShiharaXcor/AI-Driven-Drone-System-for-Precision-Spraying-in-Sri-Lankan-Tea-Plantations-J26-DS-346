"""Is there anything for the agent to learn about strip order?  For unseen test fields, at the search planner's best row direction,
score the three orders the agent can pick (plain, flat first, steep first) and also the searched order of flatfirst.py.
Run from c3app/backend:  C3_SCENARIO=a10 python3 order_oracle.py [n_fields]"""
import os, sys, collections
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import agent_env as A1, agent_env_v2 as A2, train_agent as T, flatfirst as FF
from engine import Frame, Flight

n = int(sys.argv[1]) if len(sys.argv) > 1 else 30
best_cnt = collections.Counter(); g_rule, g_search, spread, ff_win = [], [], [], []
for k, f in enumerate(T.make_fields(T.tile(), 9000, n, T.EVAL_COLS)):
    P = A1.make_problem(f)
    pl = A1.run_planner(P, coarse=True)
    if pl is None: continue
    e_pl, _, th, fr_, fd = pl
    fr = Frame(P, float(th)); fl = Flight(fr)
    E = {}
    for mode, name in enumerate(A2.ORDER_NAMES):
        o = A2.strip_order(P, fr, fr_, mode)
        e, _ = FF.energy(fl, fr, (fr_, fd), o if o is not None else (list(range(len(fr.rows())))[::-1] if fr_ else list(range(len(fr.rows())))), True)
        E[name] = e
    sr = FF.flat_first(P, float(th), (fr_, fd), True)
    E["searched order"] = sr["e_best"]
    b = min(E, key=E.get); best_cnt[b] += 1
    ff_win.append((1 - E["flat first"] / E["plain order"]) * 100)
    g_rule.append((1 - min(E["flat first"], E["steep first"], E["plain order"]) / E["plain order"]) * 100)
    g_search.append((1 - E["searched order"] / E["plain order"]) * 100)
    spread.append(np.std(sr["chunk_slopes"]))
    print(f"field {k+1}/{n}", flush=True)
print("\ncheapest order per field:", dict(best_cnt))
print(f"best of the three agent choices vs plain order: mean {np.mean(g_rule):.2f} %  median {np.median(g_rule):.2f} %  max {np.max(g_rule):.2f} %")
print(f"searched order vs plain order:                  mean {np.mean(g_search):.2f} %  median {np.median(g_search):.2f} %  max {np.max(g_search):.2f} %")
print(f"flat first vs plain order: better by >0.3 % on {sum(1 for x in ff_win if x > .3)} of {len(ff_win)} fields, worse by >0.3 % on {sum(1 for x in ff_win if x < -.3)}; mean {np.mean(ff_win):+.2f} %")
