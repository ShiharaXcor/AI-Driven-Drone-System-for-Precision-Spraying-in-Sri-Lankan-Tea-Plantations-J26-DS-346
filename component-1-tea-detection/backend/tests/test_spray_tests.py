from fastapi.testclient import TestClient
from app import spray_tests as st
from app.decision import decide as real_decide
from app.main import app
from app.services import STATE

client = TestClient(app)
KEY = {"x-api-key": "dev-key"}


def test_all_spray_scenarios_pass_and_state_is_restored():
    STATE.update(emergency=False, manual=None, mission_id=None)
    r = client.post("/api/spray-tests/run", headers=KEY).json()
    assert r["total"] >= 450
    assert r["failed"] == 0, r["failures"]
    assert STATE["emergency"] is False and STATE["manual"] is None


def test_run_needs_api_key():
    assert client.post("/api/spray-tests/run").status_code == 401


def test_broken_engine_is_caught(monkeypatch):
    # Engine that always says SPRAY must fail the safety scenarios
    monkeypatch.setattr(st, "decide", lambda dets, **kw: ("SPRAY", "broken"))
    r = client.post("/api/spray-tests/run", headers=KEY).json()
    assert r["failed"] > 100
    monkeypatch.setattr(st, "decide", real_decide)
    assert client.post("/api/spray-tests/run", headers=KEY).json()["failed"] == 0