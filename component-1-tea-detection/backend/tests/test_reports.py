import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services import STATE

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_state():
    STATE.update(emergency=False, manual=None, mission_id=None)
    yield


def _decide(dets):
    return client.post("/api/decide", json={"detections": [{"cls": c, "conf": v} for c, v in dets]})


def test_mission_report_and_csv_export():
    mid = client.post("/api/missions/start?name=report-test").json()["mission_id"]
    _decide([("tea_plant", 0.9)])
    _decide([("tea_plant", 0.9), ("person", 0.6)])
    _decide([("tea_plant", 0.6)])
    client.post("/api/missions/end")

    r = client.get(f"/api/report/mission/{mid}").json()
    assert r["total_events"] == 3
    assert r["counts"] == {"SPRAY": 1, "NO_SPRAY": 1, "UNCERTAIN": 1}
    assert r["critical_alerts"] >= 1

    lines = client.get(f"/api/export/events.csv?mission_id={mid}").text.splitlines()
    assert lines[0].startswith("id,") and len(lines) == 4


def test_unknown_mission_is_404():
    assert client.get("/api/report/mission/999999").status_code == 404