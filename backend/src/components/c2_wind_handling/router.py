from fastapi import APIRouter

router = APIRouter(tags=["C2 - Wind handling"])


@router.get("/health")
def health():
    return {"component": "c2_wind_handling", "status": "ok"}