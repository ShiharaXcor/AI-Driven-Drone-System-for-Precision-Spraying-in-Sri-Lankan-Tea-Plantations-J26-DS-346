# server.py - Component 3 web backend (FastAPI)
#
# Run (from the c3app folder, venv active):
#   pip install fastapi uvicorn
#   python3 -m uvicorn backend.server:app --port 8000
# then open http://localhost:8000
#
# API
#   GET  /api/evidence                   validation numbers for the Evidence page
#   GET  /api/sites                      terrain sites
#   GET  /api/sites/{id}?z_scale=1       height grid of a site
#   GET  /api/example/{id}               a ready-made demo request
#   POST /api/plan                       plan a mission (polygon, trees, depot, drone settings) -> compare strategies
#   GET  /api/mission/{mid}/stream       live telemetry (server-sent events) for one strategy
#   POST /api/mission/{mid}/obstacle     a new obstacle appears mid-flight: re-plan the rest of the mission
import os, sys, json, time, uuid, asyncio, threading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import engine as G
import geo
import base64, hashlib, math

HERE = os.path.dirname(os.path.abspath(__file__))
FRONT = os.path.abspath(os.path.join(HERE, "..", "frontend"))

app = FastAPI(title="Component 3 - energy-aware spray mission planner")
planner = G.MissionPlanner()
MISSIONS = {}            # mission id -> {strategy -> info}
LOCK = threading.Lock()


class Tree(BaseModel):
    x: float
    y: float
    r: float = 2.0


class PlanReq(BaseModel):
    site: str
    polygon: list[list[float]]
    trees: list[Tree] = []
    depot: list[float]
    params: dict = {}
    z_scale: float = 1.0
    agent_model: str | None = None      # name of a trained agent in c3app/agents (None = no agent)


class ObstacleReq(BaseModel):
    strategy: str = "optimised"
    step: int
    x: float
    y: float
    r: float = 2.5


def _py(o):
    if isinstance(o, dict):
        return {k: _py(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_py(v) for v in o]
    if isinstance(o, np.ndarray):
        return _py(o.tolist())
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    return o


@app.get("/api/agents")
def agents():
    try:
        import agent_route as AR
        return AR.list_agents()
    except Exception as e:
        return []


@app.get("/api/evidence")
def evidence():
    """numbers for the 'Evidence and limits' page: real validation results, agent test results, assumptions"""
    out = dict(
        facts=dict(flights_raw=981, flights_kept=679, flights_full_tank=537, calib_n=375, test_n=162,
                   srtm_m=float(G.SRTM_DX), grid_m=G.GRID),
        energy=None, agents=[], assumptions=G.ASSUMPTIONS)
    p = os.path.join(HERE, "..", "evidence", "energy_validation.json")
    if os.path.exists(p):
        try:
            out["energy"] = json.load(open(p))
        except Exception:
            pass
    try:
        import agent_route as AR
        out["agents"] = AR.list_agents()
    except Exception:
        pass
    return JSONResponse(_py(out))


@app.get("/api/sites")
def sites():
    return planner.sites.listing()


@app.get("/api/sites/{sid}")
def site(sid: str, z_scale: float = 1.0):
    try:
        z = planner.sites.get(sid, z_scale)
    except StopIteration:
        raise HTTPException(404, "unknown site")
    return dict(id=sid, dx=G.GRID, size=planner.sites.size_of(sid), z=np.round(z, 2).tolist(),
                imagery=os.path.exists(_img_path(sid)))


@app.get("/api/example/{sid}")
def example(sid: str, z_scale: float = 1.0):
    return G.example_request(sid, z_scale, planner.sites.size_of(sid))


def _img_path(sid):
    return os.path.join(planner.sites._cache_dir(), f"img_{sid}.png")


@app.get("/api/sites/{sid}/imagery.png")
def imagery(sid: str):
    p = _img_path(sid)
    if not os.path.exists(p):
        raise HTTPException(404, "no imagery for this site")
    return FileResponse(p, media_type="image/png")


class EstateReq(BaseModel):
    lat: float | None = None
    lon: float | None = None
    size: float = 300.0
    kml_b64: str | None = None          # a .kml or .kmz file, base64


@app.post("/api/estate")
def estate(req: EstateReq):
    """Create a site from latitude/longitude or a Google Earth KML/KMZ boundary."""
    polygon_ll, pts = None, []
    if req.kml_b64:
        try:
            k = geo.parse_kml(base64.b64decode(req.kml_b64))
        except ValueError as e:
            raise HTTPException(400, str(e))
        polygon_ll, pts = k["polygon"], k["points"]
        if polygon_ll:
            a = np.asarray(polygon_ll)
            lon0, lat0 = (a[:, 0].min() + a[:, 0].max()) / 2, (a[:, 1].min() + a[:, 1].max()) / 2
        else:
            lon0, lat0 = pts[0]["lon"], pts[0]["lat"]
    elif req.lat is not None and req.lon is not None:
        lat0, lon0 = req.lat, req.lon
    else:
        raise HTTPException(400, "give a latitude and longitude, or a KML file")
    if not (-60 <= lat0 <= 60 and -180 <= lon0 <= 180):
        raise HTTPException(400, "latitude must be between -60 and 60 and longitude between -180 and 180")
    size = float(req.size)
    poly_local = None
    if polygon_ll:
        a = np.asarray(polygon_ll)
        x, y = geo.to_local(a[:, 0], a[:, 1], lon0, lat0)
        poly_local = np.stack([x, y], 1)
        ext = max(np.ptp(x), np.ptp(y))
        size = float(min(600, max(200, math.ceil((ext + 100) / 50) * 50)))
        if ext + 20 > size:
            raise HTTPException(400, "the field is too large for one site (limit about 500 m across); split it into parts")
    size = float(min(600, max(150, round(size / 5) * 5)))
    sid = "est-" + hashlib.md5(f"{lat0:.5f},{lon0:.5f},{size}".encode()).hexdigest()[:8]
    warnings = []
    try:
        z = geo.site_dem(lat0, lon0, size, G.GRID)
    except RuntimeError as e:
        raise HTTPException(502, str(e))
    has_img = False
    try:
        geo.site_imagery(lat0, lon0, size).save(_img_path(sid))
        has_img = True
    except Exception as e:
        warnings.append(f"Satellite imagery not available ({e}). The terrain is shown by slope colours instead.")
    planner.sites.add_custom(sid, f"Estate {lat0:.4f}, {lon0:.4f}", size, z, lat0, lon0, has_img)
    out = dict(site=planner.sites.meta(sid), warnings=warnings, polygon=None, trees=[], depot=None)
    if poly_local is not None:
        P = (poly_local + size / 2).round(1)
        out["polygon"] = P.tolist()
        area = G.poly_area(P)
        out["area_ha"] = area / 1e4
        if area > 8e4:
            warnings.append("The field is larger than 8 ha: the planner accepts up to 8 ha per field.")
    for p in pts:
        nm = p["name"].lower()
        lx, ly = geo.to_local(p["lon"], p["lat"], lon0, lat0)
        xy = [round(float(lx) + size / 2, 1), round(float(ly) + size / 2, 1)]
        if any(w in nm for w in ("depot", "refill", "home", "base", "truck")):
            out["depot"] = xy
        elif "tree" in nm or "obstacle" in nm or "pole" in nm:
            m = __import__("re").search(r"r\s*=\s*([0-9.]+)", nm)
            out["trees"].append(dict(x=xy[0], y=xy[1], r=float(m.group(1)) if m else 2.0))
    return out


def _check(req: PlanReq):
    try:
        size = planner.sites.size_of(req.site)
    except Exception:
        raise HTTPException(404, "unknown site")
    if len(req.polygon) < 3:
        raise HTTPException(400, "the field needs at least 3 corners")
    for p in req.polygon + [req.depot]:
        if not (0 <= p[0] <= size and 0 <= p[1] <= size):
            raise HTTPException(400, f"all points must lie inside the {size:.0f} m site")
    if G.poly_area(req.polygon) < 400:
        raise HTTPException(400, "the field is smaller than 0.04 ha")
    if G.poly_area(req.polygon) > 8 * 10000:
        raise HTTPException(400, "the field is larger than 8 ha")


@app.post("/api/plan")
def plan(req: PlanReq):
    _check(req)
    keep = {}
    d = req.model_dump()
    try:
        out = planner.plan(d, keep=keep)
    except RuntimeError as e:
        raise HTTPException(422, str(e))
    mid = uuid.uuid4().hex[:10]
    with LOCK:
        MISSIONS[mid] = keep
        if len(MISSIONS) > 40:
            MISSIONS.pop(next(iter(MISSIONS)))
    out["mission_id"] = mid
    return JSONResponse(_py(out))


@app.get("/api/mission/{mid}/stream")
async def stream(mid: str, strategy: str = "optimised", start: int = 0, speed: float = 20.0):
    info = MISSIONS.get(mid, {}).get(strategy)
    if info is None:
        raise HTTPException(404, "unknown mission or strategy")
    r = info["route"]
    n = len(r["x"])
    total_spray = sum(1 for k in r["kind"] if k == 1) or 1

    async def gen():
        spray_done = sum(1 for k in r["kind"][:start] if k == 1)
        i = max(0, start)
        yield "retry: 3000\n\n"
        last_sortie = r["sortie"][i] if i < n else 1
        while i < n:
            if r["kind"][i] == 1:
                spray_done += 1
            ev = None
            if r["sortie"][i] != last_sortie:
                ev = f"Sortie {r['sortie'][i]} starts (refilled at the depot)"
                last_sortie = r["sortie"][i]
            kind = {0: "transit", 1: "spraying", 2: "turning"}[r["kind"][i]]
            f = dict(i=i, n=n, t=r["t"][i], x=r["x"][i], y=r["y"][i], alt=r["alt"][i], liq=r["liq"][i], bat=r["bat"][i],
                     kind=kind, sortie=r["sortie"][i], progress=spray_done / total_spray,
                     eta=max(0.0, r["t"][-1] - r["t"][i]), event=ev)
            yield f"data: {json.dumps(f)}\n\n"
            if i + 1 < n:
                await asyncio.sleep(max(0.005, (r["t"][i + 1] - r["t"][i]) / max(speed, 0.1)))
            i += 1
        yield "data: " + json.dumps(dict(done=True)) + "\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/api/mission/{mid}/obstacle")
def obstacle(mid: str, ob: ObstacleReq):
    with LOCK:
        info = MISSIONS.get(mid, {}).get(ob.strategy)
    if info is None:
        raise HTTPException(404, "unknown mission or strategy")
    tree = dict(x=ob.x, y=ob.y, r=ob.r)
    t0 = time.time()
    try:
        info2, merged, m = planner.replan(info, ob.step, tree)
    except RuntimeError as e:
        raise HTTPException(422, str(e))
    with LOCK:
        MISSIONS[mid][ob.strategy] = info2
    m["replan_seconds"] = time.time() - t0
    return JSONResponse(_py(dict(route=merged, metrics=m, trees=[dict(x=float(a), y=float(b), r=float(r_)) for (a, b), r_ in
                                                                  zip(info2["P"].trees, info2["P"].rad)])))


@app.get("/")
def index():
    return FileResponse(os.path.join(FRONT, "index.html"))


app.mount("/static", StaticFiles(directory=FRONT), name="static")
