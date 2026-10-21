from fastapi import APIRouter, Header, HTTPException, Depends
from .. import config
from ..db import Session, Alert
from ..services import STATE, relay, gps

router = APIRouter(prefix="/api", tags=["controls"])


def require_key(x_api_key: str = Header(default="")):
    if x_api_key != config.API_KEY:
        raise HTTPException(401, "Invalid or missing API key")


@router.post("/emergency/{on}")
def emergency(on: bool, x_api_key: str = Header(default="")):
    # Anyone can STOP. Only an authorised user can RELEASE.
    if not on and x_api_key != config.API_KEY:
        raise HTTPException(401, "Releasing the emergency stop requires the API key")
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


@router.get("/status")
def status():
    return {**STATE, "relay_on": relay.on, "relay_simulated": relay.simulated}


@router.get("/gps")
def api_gps():
    return gps.read()