# bench_fields.py - plans 24 random fields (4 sites, 0.2-1.2 ha, real and 2.5x steeper terrain) and prints the saving of the
# optimised route against the standard route, lever by lever.   Run from c3app:  python3 tools/bench_fields.py
import sys,os,math,time,json
import os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'backend'))
import numpy as np, engine as G
mp=G.MissionPlanner()
rng=np.random.default_rng(5)
class _:pass
rows=[]
def rand_field(area_ha):
    # irregular convex-ish polygon of given area inside site, random orientation
    w=math.sqrt(area_ha*1e4)*rng.uniform(0.8,1.4); h=area_ha*1e4/w
    th=rng.uniform(0,math.pi)
    c=np.array([150.0,150.0])+rng.uniform(-30,30,2)
    pts=[]
    for k in range(5+rng.integers(0,3)):
        a=2*math.pi*k/6+rng.uniform(-.25,.25)
        pts.append([c[0]+0.5*w*math.cos(a)*rng.uniform(.85,1.1),c[1]+0.5*h*math.sin(a)*rng.uniform(.85,1.1)])
    pts=np.array(pts)-c; R=np.array([[math.cos(th),-math.sin(th)],[math.sin(th),math.cos(th)]]); pts=pts@R.T+c
    return pts.tolist()
for si,site in enumerate(mp.sites.defs):
    for area in (0.5,1.0,2.0):
        for zs in (1.0,2.5):
            poly=rand_field(area)
            trees=[]
            while len(trees)<int(8*area)+4:
                p=rng.uniform(np.min(poly,0),np.max(poly,0))
                if G.point_in_poly(np.array([p[0]]),np.array([p[1]]),np.array(poly))[0] and all(math.hypot(p[0]-t['x'],p[1]-t['y'])>12 for t in trees):
                    trees.append(dict(x=float(p[0]),y=float(p[1]),r=float(rng.uniform(1.5,3))))
            depot=[float(np.min(np.array(poly)[:,0])-12),float(np.min(np.array(poly)[:,1])-12)]
            depot=[max(5,depot[0]),max(5,depot[1])]
            req=dict(site=site['id'],polygon=poly,trees=trees,depot=depot,params={},z_scale=zs)
            try:
                o=mp.plan(req)
            except Exception as e:
                print('FAIL',site['name'],area,zs,e); json.dump(req,open('bench_fail.json','w')); continue
            S={s['id']:s['metrics'] for s in o['strategies']}
            sav=(1-S['optimised']['energy_pct']/S['standard']['energy_pct'])*100
            lv={l['label'][:12]:l['vs_standard_pct'] for l in o['levers']}
            rows.append(dict(site=site['name'],area=o['field_ha'],zs=zs,sav=sav,angle=o['levers'][1]['vs_standard_pct'],trim=o['levers'][4]['vs_standard_pct'],fill=o['levers'][2]['vs_standard_pct'],
                             depot=o['depot_advice']['saving_pct'] if o['depot_advice'] else 0,sort=S['optimised']['sorties'],cov=S['optimised']['coverage'],
                             hits=S['optimised']['contact_steps'],fixhits=S['fixed']['contact_steps']))
            r=rows[-1]; print(f"{r['site']:22s} {r['area']:.2f} ha z{r['zs']}  opt {r['sav']:+5.1f}%  angle {r['angle']:+4.1f} fullTanks {r['trim']:+4.1f} fill {r['fill']:+5.1f} depot {r['depot']:+4.1f}  sorties {r['sort']} cov {100*r['cov']:.1f} hits {r['hits']} fixedhits {r['fixhits']}",flush=True)
json.dump(rows,open('bench_fields.json','w'))
a=np.array([[r['sav'],r['angle'],r['trim'],r['fill'],r['depot']] for r in rows])
print('mean',a.mean(0),'min',a.min(0),'max',a.max(0),'n',len(rows))
