import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services import STATE

client = TestClient(app)
TEA = {"detections": [{"cls": "tea_plant", "conf": 0.9}]}
KEY = {"x-api-key": "dev-key"}


@pytest.fixture(autouse=True)
def reset_state():
    STATE.update(emergency=False, manual=None, mission_id=None)
    yield


def test_health():
    assert client.get("/api/health").json() == {"ok": True}


def test_clean_tea_sprays():
    r = client.post("/api/decide", json=TEA).json()
    assert r["decision"] == "SPRAY" and r["spray_status"] == "ON"


def test_person_stops_spray_and_raises_alert():
    body = {"detections": [{"cls": "tea_plant", "conf": 0.9}, {"cls": "person", "conf": 0.6}]}
    r = client.post("/api/decide", json=body).json()
    assert r["decision"] == "NO_SPRAY" and r["spray_status"] == "OFF"
    assert client.get("/api/alerts").json()[0]["priority"] == "critical"


def test_emergency_overrides_ai_and_needs_key_to_release():
    client.post("/api/emergency/true")
    assert client.post("/api/decide", json=TEA).json()["spray_status"] == "OFF"
    assert client.post("/api/emergency/false").status_code == 401
    assert client.post("/api/emergency/false", headers=KEY).status_code == 200


def test_manual_override_needs_key():
    assert client.post("/api/manual/ON").status_code == 401
    assert client.post("/api/manual/ON", headers=KEY).status_code == 200
    assert client.post("/api/decide", json=TEA).json()["reason"] == "Manual override"


def test_event_and_detections_are_saved():
    r = client.post("/api/decide", json=TEA).json()
    d = client.get(f"/api/events/{r['event_id']}").json()
    assert d["decision"] == "SPRAY" and d["detections"][0]["cls"] == "tea_plant"


def test_mission_links_events():
    mid = client.post("/api/missions/start?name=test").json()["mission_id"]
    r = client.post("/api/decide", json=TEA).json()
    assert client.get(f"/api/events/{r['event_id']}").json()["mission_id"] == mid
    client.post("/api/missions/end")


def test_summary_counts():
    client.post("/api/decide", json=TEA)
    s = client.get("/api/summary").json()
    assert s["total"] >= 1 and "SPRAY" in s["counts"]