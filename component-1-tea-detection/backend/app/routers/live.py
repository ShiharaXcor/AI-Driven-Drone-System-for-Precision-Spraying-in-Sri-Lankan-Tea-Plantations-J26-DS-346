import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ..camera import camera
from ..db import Session, Event, Alert, row_to_dict
from ..services import STATE, relay

router = APIRouter(tags=["live"])


def _snapshot(last_ev, last_al):
    with Session() as s:
        if last_ev == 0:     # first message: the latest 20 events, oldest first
            evs = list(reversed(s.query(Event).order_by(Event.id.desc()).limit(20).all()))
            als = list(reversed(s.query(Alert).order_by(Alert.id.desc()).limit(20).all()))
        else:
            evs = s.query(Event).filter(Event.id > last_ev).order_by(Event.id).limit(50).all()
            als = s.query(Alert).filter(Alert.id > last_al).order_by(Alert.id).limit(50).all()
        events = [row_to_dict(e) for e in evs]
        alerts = [row_to_dict(a) for a in als]
    return events, alerts


@router.websocket("/ws/live")
async def live(ws: WebSocket):
    """Pushes new events and alerts once per second, plus the current control status."""
    await ws.accept()
    last_ev = last_al = 0
    try:
        while True:
            events, alerts = await asyncio.to_thread(_snapshot, last_ev, last_al)
            if events:
                last_ev = events[-1]["id"]
            if alerts:
                last_al = alerts[-1]["id"]
            await ws.send_json({"status": {**STATE, "relay_on": relay.on, "camera": camera.status()},
                                "events": events, "alerts": alerts})
            try:                                          # doubles as the 1 s pause and disconnect check
                await asyncio.wait_for(ws.receive_text(), timeout=1.0)
            except asyncio.TimeoutError:
                pass
    except WebSocketDisconnect:
        pass