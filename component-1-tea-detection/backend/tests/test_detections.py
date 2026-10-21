from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_detections_rows_have_class_decision_and_reason():
    body = {"detections": [{"cls": "tea_plant", "conf": 0.9}, {"cls": "person", "conf": 0.6}]}
    client.post("/api/decide", json=body)
    rows = client.get("/api/detections?limit=10").json()
    assert rows and {"cls", "conf", "decision", "reason", "ts", "lat", "lon"} <= set(rows[0])