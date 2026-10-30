from fastapi import APIRouter

router = APIRouter(tags=["C1 - Spray detection"])


@router.get("/health")
def health():
    return {"component": "c1_spray_detection", "status": "ok"}