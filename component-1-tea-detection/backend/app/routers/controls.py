from fastapi import APIRouter, Depends, Header, HTTPException
from .. import config, vision
from ..auth import is_authorized, require_key
from ..camera import camera
from ..db import Session, Alert
from ..services import STATE, relay, gps

router = APIRouter(prefix="/api", tags=["controls"])


@router.post("/emergency/{on}")
def emergency(on: bool, x_api_key: str = Header(default=""), authorization: str = Header(default="")):
    # Anyone can STOP. Only an authorised operator can RELEASE.
    if not on and not is_authorized(x_api_key, authorization):
        raise HTTPException(401, "Releasing the emergency stop requires login or the API key")
    STATE["emergency"] = on
    if on:
        relay.set(False)
        p = gps.read()
        with Session() as s:
            s.add(Alert(priority="critical", message="Emergency stop activated", lat=p["lat"], lon=p["lon"]))
            s.commit()
    return STATE


@router.post("/manual/{mode}", dependencies=[Depends(require_key)])     # ON | OFF | AUTO
def manual(mode: str):
    if mode not in ("ON", "OFF", "AUTO"):
        raise HTTPException(400, "mode must be ON, OFF or AUTO")
    STATE["manual"] = None if mode == "AUTO" else mode
    relay.set(STATE["manual"] == "ON" and not STATE["emergency"])
    return STATE


def _file_info(p):
    return {"path": str(p), "exists": p.exists(),
            "size_mb": round(p.stat().st_size / 1e6, 1) if p.exists() else None}


@router.get("/status")
def status():
    det = vision._detector.mode if vision._detector else "not loaded yet"
    return {**STATE, "relay_on": relay.on, "relay_simulated": relay.simulated,
            "detector_mode": det, "shadow_method": "unet" if config.SHADOW_MODEL.exists() else "threshold",
            "camera": camera.status()}


@router.get("/models")
def models():
    """Shows whether your trained weights are in place (they switch the system out of demo mode)."""
    return {"main_model": _file_info(config.MODEL_PATH), "shadow_model": _file_info(config.SHADOW_MODEL),
            "detector_mode": vision._detector.mode if vision._detector else "not loaded yet",
            "shadow_method": "unet" if config.SHADOW_MODEL.exists() else "threshold"}


@router.get("/gps")
def api_gps():
    return gps.read()