from fastapi import APIRouter
from ..decision import decide, Det
from ..schemas import DecideIn
from ..services import finalize, gps

router = APIRouter(prefix="/api", tags=["decision"])


@router.post("/decide")
def api_decide(body: DecideIn):
    dets = [Det(d.cls, d.conf) for d in body.detections]
    decision, reason = decide(dets, geofence_ok=body.geofence_ok, image_ok=body.image_ok)
    pos = gps.read()
    if body.lat is not None and body.lon is not None:
        pos = {"lat": body.lat, "lon": body.lon, "alt": 0}
    return finalize(decision, reason, dets, pos)