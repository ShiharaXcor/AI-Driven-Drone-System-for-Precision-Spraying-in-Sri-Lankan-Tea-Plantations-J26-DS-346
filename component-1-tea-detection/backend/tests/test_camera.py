import time
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
KEY = {"x-api-key": "dev-key"}


def test_missing_camera_fails_safely():
    assert client.post("/api/camera/start?index=99", headers=KEY).status_code == 200
    s = {}
    for _ in range(80):
        s = client.get("/api/camera/status").json()
        if not s["running"]:
            break
        time.sleep(0.25)
    assert s["running"] is False and "Cannot open" in (s["last_error"] or "")
    client.post("/api/camera/stop", headers=KEY)


def test_camera_control_needs_key():
    assert client.post("/api/camera/start").status_code == 401