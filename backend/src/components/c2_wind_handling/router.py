"""Component 2 - API routes. They appear under /api/c2/... (see components/router.py)."""
import math

import requests
from fastapi import APIRouter, HTTPException

from src.components.c2_wind_handling.compensation import compensation as rec
from src.components.c2_wind_handling.schemas import CurveIn, RecommendIn
from src.components.c2_wind_handling.wind_prediction.predictor import predict_drift

router = APIRouter(tags=["C2 - Wind handling"])

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


@router.get("/health")
def health():
    return {"component": "c2_wind_handling", "status": "ok"}


@router.post("/recommend")
def recommend_endpoint(x: RecommendIn):
    try:
        return to_json_safe(rec.recommend(**x.model_dump()))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/drift-curve")
def drift_curve(x: CurveIn):
    """Predicted drift for each droplet class across crosswind 0.5-6.5 m/s (for the chart)."""
    crosswinds = [round(0.5 + 0.25 * i, 2) for i in range(25)]   # 0.5 ... 6.5
    rows = []
    for cw in crosswinds:
        row = {"crosswind": cw}
        for d in rec.DROPLETS_FINE_TO_COARSE:
            row[d] = round(float(predict_drift(cw, x.height_m, x.swath_m, x.temp_c, x.rh_pct, d)), 2)
        rows.append(row)
    return {"rows": rows, "classes": rec.DROPLETS_FINE_TO_COARSE}


@router.get("/regions")
def regions():
    return list(REGIONS)


@router.get("/weather/{region}")
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