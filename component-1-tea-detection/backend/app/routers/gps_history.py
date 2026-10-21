from fastapi import APIRouter
from ..db import Session, GpsLog, row_to_dict

router = APIRouter(prefix="/api/gps", tags=["gps"])


@router.get("/history")
def history(limit: int = 200):
    with Session() as s:
        rows = s.query(GpsLog).order_by(GpsLog.id.desc()).limit(limit).all()
        return [row_to_dict(r) for r in rows]


@router.get("/quality")
def quality():
    with Session() as s:
        rows = s.query(GpsLog).order_by(GpsLog.id.desc()).limit(5000).all()
    if not rows:
        return {"fixes": 0}
    hd = [r.hdop for r in rows if r.hdop is not None]
    st = [r.sats for r in rows if r.sats is not None]
    good = [r for r in rows if (r.hdop or 99) <= 2.5 and (r.sats or 0) >= 6]
    sources = {}
    for r in rows:
        sources[r.source] = sources.get(r.source, 0) + 1
    return {"fixes": len(rows),
            "avg_hdop": round(sum(hd) / len(hd), 2) if hd else None,
            "avg_sats": round(sum(st) / len(st), 1) if st else None,
            "good_fix_rate": round(len(good) / len(rows), 3),
            "sources": sources}