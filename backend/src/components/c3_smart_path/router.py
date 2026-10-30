from fastapi import APIRouter

router = APIRouter(tags=["C3 - Smart path"])


@router.get("/health")
def health():
    return {"component": "c3_smart_path", "status": "ok"}