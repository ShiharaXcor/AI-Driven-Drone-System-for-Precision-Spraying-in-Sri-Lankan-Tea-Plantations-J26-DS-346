import asyncio
import cv2
import numpy as np
from fastapi import APIRouter, UploadFile, File, HTTPException
from .. import config
from ..pipeline import run_pipeline

router = APIRouter(prefix="/api", tags=["inference"])


@router.post("/infer")
async def infer(file: UploadFile = File(...), geofence_ok: bool = True):
    data = await file.read()
    if len(data) > config.MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, f"Image larger than {config.MAX_UPLOAD_MB} MB")
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(400, "File is not a valid image")
    # Heavy work runs in a worker thread, so live updates and other requests keep working
    return await asyncio.to_thread(run_pipeline, img, geofence_ok)