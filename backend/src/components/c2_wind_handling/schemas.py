"""Component 2 - input shapes for the API (FastAPI checks these automatically)."""
from pydantic import BaseModel, Field


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