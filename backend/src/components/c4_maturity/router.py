from fastapi import APIRouter

router = APIRouter(tags=["C4 - Maturity"])


@router.get("/health")
def health():
    return {"component": "c4_maturity", "status": "ok"}