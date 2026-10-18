# speed_sweep.py - how much of the efficiency depends only on the speed cap?
# Runs the fixed lawnmower route at several speed caps, with and without the
# base->field->base legs.  No learning involved: this is the effect of the
# energy model's (very small) speed dependence, reported so it is not mistaken
# for something the agent learned.
#   python3 drl_agent/speed_sweep.py
import numpy as np
from tea_spray_env import TeaSprayEnv, LawnmowerPolicy, run_episode

def lawnmower(v, transit, n=30):
    env = TeaSprayEnv(terminate_on_collision=False, v_max_kmh=v, transit=transit)
    pol, res = LawnmowerPolicy(), []
    for s in range(n):
        pol.reset()
        res.append(run_episode(env, lambda o: pol.act(env), 1000 + s))
    return res

print(f"{'speed km/h':>10} {'mode':>14} {'ha/charge':>10} {'area ha':>8} {'battery %':>10} {'out %':>6} {'back %':>7}")
for transit in (False, True):
    for v in (6.4, 8.0, 10.0, 12.0):
        r = lawnmower(v, transit)
        print(f"{v:>10.1f} {'whole mission' if transit else 'in patch only':>14} "
              f"{np.mean([x['coverage_per_charge'] for x in r]):>10.3f} "
              f"{np.mean([x['area_ha'] for x in r]):>8.3f} "
              f"{np.mean([x['battery_used'] for x in r]):>10.1f} "
              f"{np.mean([x['transit_out_pct'] for x in r]):>6.1f} "
              f"{np.mean([x['return_pct'] for x in r]):>7.1f}")