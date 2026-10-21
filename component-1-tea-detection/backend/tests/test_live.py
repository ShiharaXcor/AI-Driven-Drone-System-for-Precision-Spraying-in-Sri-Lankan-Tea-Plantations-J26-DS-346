from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_live_socket_sends_status_and_recent_events():
    client.post("/api/decide", json={"detections": [{"cls": "tea_plant", "conf": 0.9}]})
    with client.websocket_connect("/ws/live") as ws:
        msg = ws.receive_json()
    assert "status" in msg and "emergency" in msg["status"]
    assert msg["events"] and msg["events"][-1]["decision"]