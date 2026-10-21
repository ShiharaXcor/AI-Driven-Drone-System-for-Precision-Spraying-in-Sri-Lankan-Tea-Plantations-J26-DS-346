from .db import Session, Event, DetectionRow, Alert
from .decision import CFG
from .relay import Relay
from .gps import GPS

STATE = {"emergency": False, "manual": None, "mission_id": None}   # manual: None | "ON" | "OFF"
relay, gps = Relay(), GPS()


def resolve_control(decision, reason):
    """Control priority: emergency > manual > AI. Returns (decision, reason, spray_status)."""
    if STATE["emergency"]:
        return "NO_SPRAY", "Emergency stop active", "OFF"
    if STATE["manual"]:
        return decision, "Manual override", STATE["manual"]
    return decision, reason, ("ON" if decision == "SPRAY" else "OFF")


def finalize(decision, reason, dets, pos, extra=None):
    """Apply control priority, drive the relay, log the event and raise alerts."""
    decision, reason, status = resolve_control(decision, reason)
    relay.set(status == "ON")

    best = lambda c: max([d.conf for d in dets if d.cls == c], default=0.0)
    with Session() as s:
        ev = Event(mission_id=STATE["mission_id"], lat=pos["lat"], lon=pos["lon"], alt=pos.get("alt", 0),
                   decision=decision, reason=reason, spray_status=status,
                   tea_conf=best("tea_plant"), person_conf=best("person"), animal_conf=best("animal"),
                   **(extra or {}))
        s.add(ev)
        s.flush()
        for d in dets:
            b = d.bbox or (None, None, None, None)
            s.add(DetectionRow(event_id=ev.id, cls=d.cls, conf=d.conf,
                               x1=b[0], y1=b[1], x2=b[2], y2=b[3]))
        if best("person") >= CFG["person_stop"]:
            s.add(Alert(priority="critical", message=f"Person detected ({best('person'):.2f}). Spray stopped.",
                        lat=pos["lat"], lon=pos["lon"]))
        if best("animal") >= CFG["animal_stop"]:
            s.add(Alert(priority="critical", message=f"Animal detected ({best('animal'):.2f}). Spray stopped.",
                        lat=pos["lat"], lon=pos["lon"]))
        s.commit()
        event_id = ev.id
    return {"event_id": event_id, "decision": decision, "reason": reason, "spray_status": status}