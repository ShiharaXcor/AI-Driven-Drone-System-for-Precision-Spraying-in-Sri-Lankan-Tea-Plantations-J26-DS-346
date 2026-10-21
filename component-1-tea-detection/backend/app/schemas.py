from typing import List, Optional
from pydantic import BaseModel


class DetIn(BaseModel):
    cls: str
    conf: float


class DecideIn(BaseModel):
    detections: List[DetIn]
    lat: Optional[float] = None
    lon: Optional[float] = None
    geofence_ok: bool = True
    image_ok: bool = True