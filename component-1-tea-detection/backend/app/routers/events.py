import datetime as dt
from fastapi import APIRouter, HTTPException
from ..db import Session, Event, DetectionRow, Alert, Mission, row_to_dict, now
from ..services import STATE

router = APIRouter(prefix="/api", tags=["events"])


@router.get("/events")
def events(limit: int = 100):
    with Session() as s:
        rows = s.query(Event).order_by(Event.id.desc()).limit(limit).all()
        return [row_to_dict(r) for r in rows]


@router.get("/events/{event_id}")
def event_detail(event_id: int):
    with Session() as s:
        ev = s.get(Event, event_id)
        if not ev:
            raise HTTPException(404, "No such event")
        dets = s.query(DetectionRow).filter(DetectionRow.event_id == event_id).all()
        return {**row_to_dict(ev), "detections": [row_to_dict(d) for d in dets]}

@router.get("/detections")
def detections(limit: int = 500):
    """One row per detected object, joined with its event (used by the Logs page)."""
    with Session() as s:
        rows = (s.query(DetectionRow, Event)
                 .join(Event, Event.id == DetectionRow.event_id)
                 .order_by(DetectionRow.id.desc()).limit(limit).all())
        return [{"id": d.id, "event_id": e.id, "ts": e.ts.isoformat(), "cls": d.cls, "conf": d.conf,
                 "lat": e.lat, "lon": e.lon, "alt": e.alt, "decision": e.decision, "reason": e.reason,
                 "spray_status": e.spray_status, "image_url": e.image_url} for d, e in rows]


@router.get("/alerts")
def alerts(limit: int = 50):
    with Session() as s:
        rows = s.query(Alert).order_by(Alert.id.desc()).limit(limit).all()
        return [row_to_dict(r) for r in rows]


@router.post("/alerts/{alert_id}/ack")
def ack(alert_id: int):
    with Session() as s:
        a = s.get(Alert, alert_id)
        if not a:
            raise HTTPException(404, "No such alert")
        a.acked = True
        s.commit()
    return {"ok": True}


@router.post("/missions/start")
def mission_start(name: str = "mission"):
    with Session() as s:
        m = Mission(name=name)
        s.add(m); s.commit()
        STATE["mission_id"] = m.id
        return {"mission_id": m.id}


@router.post("/missions/end")
def mission_end():
    mid = STATE["mission_id"]
    if mid is None:
        raise HTTPException(400, "No active mission")
    with Session() as s:
        m = s.get(Mission, mid)
        m.ended_at = now()
        s.commit()
    STATE["mission_id"] = None
    return {"ended": mid}


@router.get("/summary")
def summary():
    with Session() as s:
        rows = s.query(Event).all()
    counts = {"SPRAY": 0, "NO_SPRAY": 0, "UNCERTAIN": 0}
    for r in rows:
        counts[r.decision] = counts.get(r.decision, 0) + 1
    enh = [r for r in rows if r.tea_before is not None and r.tea_after is not None]
    lat = [r.latency_ms for r in rows if r.latency_ms]
    return {"total": len(rows), "counts": counts,
            "avg_latency_ms": sum(lat) / len(lat) if lat else None,
            "enhanced_images": len(enh),
            "avg_tea_conf_gain": sum(r.tea_after - r.tea_before for r in enh) / len(enh) if enh else None}