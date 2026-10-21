from fastapi import APIRouter, Depends
from ..auth import require_key
from ..camera import camera

router = APIRouter(prefix="/api/camera", tags=["camera"])


@router.post("/start", dependencies=[Depends(require_key)])
def start(index: int | None = None, interval_s: float | None = None):
    camera.start(index, interval_s)
    return camera.status()


@router.post("/stop", dependencies=[Depends(require_key)])
def stop():
    camera.stop()
    return camera.status()


@router.get("/status")
def status():
    return camera.status()