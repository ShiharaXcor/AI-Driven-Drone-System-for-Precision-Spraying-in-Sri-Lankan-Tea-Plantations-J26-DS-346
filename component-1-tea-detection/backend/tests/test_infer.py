import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app import pipeline
from app.services import STATE

client = TestClient(app)


class FakeDetector:
    mode = "fake"

    def __init__(self, dets):
        self.dets = dets

    def predict(self, bgr, conf=0.1):
        return [dict(d) for d in self.dets]


def _jpg():
    rng = np.random.default_rng(0)
    img = (120 + rng.integers(-15, 15, (240, 320, 3))).astype(np.uint8)
    img[:, :160] = (30 + rng.integers(-5, 5, (240, 160, 3))).astype(np.uint8)   # dark half = shadow
    return cv2.imencode(".jpg", img)[1].tobytes()


@pytest.fixture(autouse=True)
def reset_state():
    STATE.update(emergency=False, manual=None, mission_id=None)
    yield


def _post(monkeypatch, dets):
    monkeypatch.setattr(pipeline, "get_detector", lambda: FakeDetector(dets))
    return client.post("/api/infer", files={"file": ("a.jpg", _jpg(), "image/jpeg")})


def test_infer_sprays_on_clean_tea(monkeypatch):
    r = _post(monkeypatch, [{"cls": "tea_plant", "conf": 0.9, "bbox": [0, 0, 50, 50]}])
    assert r.status_code == 200
    body = r.json()
    assert body["decision"] == "SPRAY" and body["shadow_ratio"] > 0.2
    assert body["image_url"].startswith("/static/out/") and body["shadow_url"]
    assert set(body["timings_ms"]) == {"model_load", "shadow", "detect_raw", "detect_enhanced", "decide"}


def test_infer_stops_for_person(monkeypatch):
    r = _post(monkeypatch, [{"cls": "tea_plant", "conf": 0.9, "bbox": [0, 0, 50, 50]},
                            {"cls": "person", "conf": 0.6, "bbox": [60, 60, 90, 120]}])
    assert r.json()["decision"] == "NO_SPRAY"


def test_infer_rejects_non_image():
    r = client.post("/api/infer", files={"file": ("a.txt", b"not an image", "text/plain")})
    assert r.status_code == 400