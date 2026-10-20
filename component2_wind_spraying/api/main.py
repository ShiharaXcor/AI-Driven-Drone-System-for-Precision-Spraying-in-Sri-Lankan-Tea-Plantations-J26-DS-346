"""Component 2 - backend API (FastAPI).

The React frontend (and later the team's shared frontend) talks to this server.
It only wraps functions that already exist: predict_drift() and recommend().

Run from the repo root (venv active):
    uvicorn component2_wind_spraying.api.main:app --reload --port 8000
Then open http://localhost:8000/docs to try every endpoint in the browser.
"""
import math

import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ..drift_model import recommend as rec
from ..drift_model.predict import predict_drift
from ..mission.simulate import simulate

app = FastAPI(title="Component 2 - Wind-adaptive spraying API", version="1.0")

# Allow the React dev server (Vite, port 5173) to call this API from the browser
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

WIND_10M_TO_2M = math.log(2 / 0.0075) / math.log(10 / 0.0075)   # same log profile as Dataset A (0.776)
REGIONS = {"Nuwara Eliya": (6.97, 80.78), "Badulla": (6.99, 81.06),
           "Kandy": (7.29, 80.63), "Ratnapura": (6.68, 80.40)}


def to_json_safe(d):
    """Turn numpy numbers (e.g. float32 from the model) into plain Python numbers."""
    out = {}
    for k, v in d.items():
        if hasattr(v, "item"):
            v = v.item()
        out[k] = v
    return out


# ---------------- request formats (FastAPI checks these automatically) ----------------
class RecommendIn(BaseModel):
    wind_ms: float = Field(..., ge=0, le=20, description="Wind speed at 2 m (m/s)")
    wind_dir_deg: float = Field(..., ge=0, lt=360, description="Direction the wind comes FROM")
    heading_deg: float = Field(..., ge=0, lt=360, description="Direction the drone flies TO")
    temp_c: float = Field(..., ge=-10, le=50)
    rh_pct: float = Field(..., ge=0, le=100)
    height_m: float = Field(2.5, gt=0, le=10)
    swath_m: float = Field(5.5, gt=0, le=20)
    droplet_class: str = "F-M"
    max_drift_m: float = Field(20.0, gt=0)


class CurveIn(BaseModel):
    height_m: float = 2.5
    swath_m: float = 5.5
    temp_c: float = 28
    rh_pct: float = 70


# ---------------- endpoints ----------------
@app.get("/health")
def health():
    return {"status": "ok", "component": 2}


@app.post("/recommend")
def recommend_endpoint(x: RecommendIn):
    try:
        return to_json_safe(rec.recommend(**x.model_dump()))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/drift-curve")
def drift_curve(x: CurveIn):
    """Predicted drift for each droplet class across crosswind 0.5-6.7 m/s (for the chart)."""
    crosswinds = [round(0.5 + 0.25 * i, 2) for i in range(25)]   # 0.5 ... 6.5
    rows = []
    for cw in crosswinds:
        row = {"crosswind": cw}
        for d in rec.DROPLETS_FINE_TO_COARSE:
            row[d] = round(float(predict_drift(cw, x.height_m, x.swath_m, x.temp_c, x.rh_pct, d)), 2)
        rows.append(row)
    return {"rows": rows, "classes": rec.DROPLETS_FINE_TO_COARSE}


@app.get("/regions")
def regions():
    return list(REGIONS)


@app.get("/weather/{region}")
def weather(region: str):
    """Current weather from Open-Meteo, wind converted from 10 m to 2 m."""
    if region not in REGIONS:
        raise HTTPException(status_code=404, detail=f"Unknown region '{region}'")
    lat, lon = REGIONS[region]
    url = ("https://api.open-meteo.com/v1/forecast"
           f"?latitude={lat}&longitude={lon}"
           "&current=temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m"
           "&wind_speed_unit=ms&timezone=Asia%2FColombo")
    try:
        c = requests.get(url, timeout=10).json()["current"]
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Weather service not reachable: {e}")
    return {"region": region, "time": c["time"], "temp_c": c["temperature_2m"],
            "rh_pct": c["relative_humidity_2m"],
            "wind_ms": round(c["wind_speed_10m"] * WIND_10M_TO_2M, 2),
            "wind_dir_deg": c["wind_direction_10m"]}



# ---------------- mission simulation ----------------
class MissionIn(BaseModel):
    center_lat: float = Field(6.955, ge=-90, le=90)
    center_lon: float = Field(80.775, ge=-180, le=180)
    length_m: float = Field(100, ge=10, le=1000)
    width_m: float = Field(60, ge=5, le=1000)
    row_bearing_deg: float = Field(0, ge=0, lt=360)
    swath_m: float = Field(5.5, gt=0, le=20)
    height_m: float = Field(2.5, gt=0, le=10)
    droplet_class: str = "F-M"
    speed_ms: float = Field(4.0, gt=0, le=15)
    temp_c: float = 28
    rh_pct: float = Field(70, ge=0, le=100)
    wind_ms: float = Field(2.5, ge=0, le=15)
    wind_dir_deg: float = Field(90, ge=0, lt=360)
    scenario: str = Field("gusty", pattern="^(gusty|steady|calm)$")
    max_drift_m: float = Field(20, gt=0)
    seed: int = 42


@app.post("/mission/simulate")
def mission_simulate(x: MissionIn):
    """Plan the spray lines over a field and simulate the whole mission step by step."""
    try:
        return simulate(**x.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))