from fastapi import APIRouter, Depends
from ..db import Session, SprayTest, row_to_dict
from ..spray_tests import run_all, summarize
from .controls import require_key

router = APIRouter(prefix="/api/spray-tests", tags=["spray tests"])


@router.post("/run", dependencies=[Depends(require_key)])
def run(reset: bool = True):
    return run_all(reset=reset)


@router.get("/summary")
def summary():
    return summarize()


@router.get("")
def list_tests(limit: int = 100, failed_only: bool = False):
    with Session() as s:
        q = s.query(SprayTest)
        if failed_only:
            q = q.filter(SprayTest.passed.is_(False))
        return [row_to_dict(r) for r in q.order_by(SprayTest.id.desc()).limit(limit).all()]