import csv
import io
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from ..db import Session, Event, Mission, Alert, SprayTest, row_to_dict, now

router = APIRouter(prefix="/api", tags=["reports"])


def _csv_response(rows, columns, filename):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(columns)
    for r in rows:
        d = row_to_dict(r)
        w.writerow([d[c] for c in columns])
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/missions")
def list_missions(limit: int = 50):
    with Session() as s:
        rows = s.query(Mission).order_by(Mission.id.desc()).limit(limit).all()
        return [row_to_dict(m) for m in rows]


@router.get("/report/mission/{mission_id}")
def mission_report(mission_id: int):
    with Session() as s:
        m = s.get(Mission, mission_id)
        if not m:
            raise HTTPException(404, "No such mission")
        evs = s.query(Event).filter(Event.mission_id == mission_id).order_by(Event.id).all()
        end = m.ended_at or now().replace(tzinfo=None)       # DB returns naive UTC times
        alerts = s.query(Alert).filter(Alert.ts >= m.started_at, Alert.ts <= end).all()

    counts = {"SPRAY": 0, "NO_SPRAY": 0, "UNCERTAIN": 0}
    for e in evs:
        counts[e.decision] = counts.get(e.decision, 0) + 1
    total = len(evs)
    lat = [e.latency_ms for e in evs if e.latency_ms]
    gains = [e.tea_after - e.tea_before for e in evs if e.tea_before is not None and e.tea_after is not None]
    return {
        "mission": row_to_dict(m),
        "duration_s": round((end - m.started_at).total_seconds(), 1),
        "total_events": total,
        "counts": counts,
        "spray_rate": round(counts["SPRAY"] / total, 3) if total else None,   # share of decisions, not field area
        "critical_alerts": sum(1 for a in alerts if a.priority == "critical"),
        "person_alerts": sum(1 for a in alerts if "Person" in a.message),
        "animal_alerts": sum(1 for a in alerts if "Animal" in a.message),
        "avg_latency_ms": round(sum(lat) / len(lat), 1) if lat else None,
        "enhanced_images": len(gains),
        "avg_tea_conf_gain": round(sum(gains) / len(gains), 4) if gains else None,
    }


@router.get("/export/events.csv")
def export_events(mission_id: int | None = None):
    with Session() as s:
        q = s.query(Event)
        if mission_id is not None:
            q = q.filter(Event.mission_id == mission_id)
        rows = q.order_by(Event.id).all()
    return _csv_response(rows, [c.name for c in Event.__table__.columns], "events.csv")


@router.get("/export/spray-tests.csv")
def export_spray_tests():
    with Session() as s:
        rows = s.query(SprayTest).order_by(SprayTest.id).all()
    return _csv_response(rows, [c.name for c in SprayTest.__table__.columns], "spray_tests.csv")