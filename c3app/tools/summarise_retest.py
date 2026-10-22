"""Table of agent gain (more hectares per 100 % battery than the usual route) under each energy setting.
a10 = tank weight at 1.0 of physics (refit scale), a05 = 0.5, a02 = 0.2. 'saved' = the model as it was when the agents were trained."""
import glob, json, os, re
import numpy as np
A = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "agents")
rows = {}
for f in sorted(glob.glob(os.path.join(A, "eval_mission_ppo_v2_s*_*.json"))):
    m = re.match(r"eval_(mission_ppo_v2_s\d)_(test|tank40)(?:_(a10|a05|a02))?\.json", os.path.basename(f))
    if not m: continue
    ag, st, sc = m.group(1), m.group(2), m.group(3) or "saved"
    s = json.load(open(f))["summary"]
    rows.setdefault((st, sc), []).append((ag, s.get("agent_gain_mean"), s.get("agent_gain_median"), s.get("wins"), s.get("n"), s.get("fields_with_contact"), s.get("planner_gain_mean")))
print(f"{'set':7s} {'energy setting':9s} {'agents':>6s} {'agent gain mean %':>18s} {'median %':>9s} {'planner mean %':>15s} {'contacts':>9s}")
for (st, sc), v in sorted(rows.items()):
    g = np.mean([x[1] for x in v]); md = np.mean([x[2] for x in v]); pl = np.mean([x[6] for x in v if x[6] is not None]) if any(x[6] is not None for x in v) else float("nan")
    print(f"{st:7s} {sc:9s} {len(v):6d} {g:18.1f} {md:9.1f} {pl:15.1f} {sum(x[5] or 0 for x in v):9d}")
print("\nGain = % more hectares per 100 % battery than the usual route.  Saving (less battery) = gain / (1 + gain).")
