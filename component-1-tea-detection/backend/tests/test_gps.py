from fastapi.testclient import TestClient
from app.main import app
from app.gps_logger import log_fix

client = TestClient(app)


def test_gps_logging_history_and_quality():
    log_fix()
    h = client.get("/api/gps/history?limit=5").json()
    assert h and h[0]["source"] in ("simulated", "ublox")
    assert client.get("/api/gps/quality").json()["fixes"] >= 1