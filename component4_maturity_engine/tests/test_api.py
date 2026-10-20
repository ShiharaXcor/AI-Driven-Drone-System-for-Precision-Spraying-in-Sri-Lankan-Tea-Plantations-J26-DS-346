"""API tests with a fake classifier (no torch needed): happy path and failure paths."""

import io
import json

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

import api.server as server


class FakeClassifier:
    classes = ["young", "medium", "mature"]

    def predict_whole(self, img):
        # brighter green -> more mature; deterministic for tests
        g = float(img[..., 1].mean())
        i = 0 if g < 85 else 1 if g < 170 else 2
        probs = [0.1, 0.1, 0.1]
        probs[i] = 0.8
        return {"maturity": self.classes[i], "confidence": 0.8,
                "probs": dict(zip(self.classes, probs)), "processing_ms": 5.0}


def jpg(green: int) -> bytes:
    img = np.zeros((240, 320, 3), np.uint8)
    img[..., 1] = green
    return cv2.imencode(".jpg", img)[1].tobytes()


@pytest.fixture
def client(tmp_path, monkeypatch):
    cfg = tmp_path / "spray.yaml"
    cfg.write_text(open(server.DEFAULT_CONFIG, encoding="utf-8").read(), encoding="utf-8")
    monkeypatch.setattr(server, "DEFAULT_CONFIG", cfg)
    monkeypatch.setattr(server, "MISSIONS_DIR", tmp_path / "missions")
    monkeypatch.setattr(server, "RUNS_DIR", tmp_path / "runs")
    server.app.state.classifier = FakeClassifier()
    server.app.state.model_error = None
    yield TestClient(server.app)
    server.app.state.classifier = None


def upload(client, *blobs, field="Block 7"):
    files = [("files", (f"p{i}.jpg", io.BytesIO(b), "image/jpeg")) for i, b in enumerate(blobs)]
    return client.post("/api/prescriptions", files=files, data={"field": field})


def test_health(client):
    r = client.get("/api/health").json()
    assert r["model_loaded"] and r["classes"] == ["young", "medium", "mature"]


def test_prescription_round_trip(client):
    r = upload(client, jpg(40), jpg(120), jpg(220))
    assert r.status_code == 201
    p = r.json()
    assert [x["spray_level"] for x in p["regions"]] == ["low", "normal", "high"]
    assert p["field"] == "Block 7" and p["summary"]["regions"] == 3

    missions = client.get("/api/missions").json()
    assert missions[0]["mission_id"] == p["mission_id"]
    full = client.get(f"/api/missions/{p['mission_id']}").json()
    assert full["regions"][0]["probs"]["young"] == 0.8
    img = client.get(f"/api/missions/{p['mission_id']}/images/1")
    assert img.status_code == 200 and img.headers["content-type"] == "image/jpeg"


def test_unreadable_files_are_reported_not_fatal(client):
    files = [("files", ("ok.jpg", io.BytesIO(jpg(40)), "image/jpeg")),
             ("files", ("bad.jpg", io.BytesIO(b"garbage"), "image/jpeg"))]
    p = client.post("/api/prescriptions", files=files).json()
    assert p["summary"]["regions"] == 1
    assert p["rejected"] == [{"image": "bad.jpg", "reason": "not a readable image"}]


def test_all_files_unreadable_gives_422(client):
    r = client.post("/api/prescriptions",
                    files=[("files", ("bad.jpg", io.BytesIO(b"x"), "image/jpeg"))])
    assert r.status_code == 422
    assert client.get("/api/missions").json() == []      # nothing half-saved


def test_model_unavailable_gives_503(client):
    server.app.state.classifier = None
    server.app.state.model_error = "Model file not found: x"
    assert upload(client, jpg(40)).status_code == 503
    assert client.get("/api/health").json()["model_loaded"] is False


def test_config_update_is_validated_and_used(client):
    assert client.put("/api/config", json={"confidence_threshold": 2}).status_code == 422
    assert client.put("/api/config", json={"mapping": {"young": "extreme", "medium": "normal",
                                                       "mature": "high"}}).status_code == 422
    assert client.put("/api/config", json={"hacker": 1}).status_code == 422
    r = client.put("/api/config", json={"confidence_threshold": 0.9})
    assert r.status_code == 200 and r.json()["confidence_threshold"] == 0.9
    p = upload(client, jpg(40)).json()            # fake confidence 0.8 < 0.9
    assert p["regions"][0]["needs_review"] and p["regions"][0]["spray_level"] == "normal"


def test_bad_mission_ids(client):
    assert client.get("/api/missions/../../etc").status_code in (400, 404)
    assert client.get("/api/missions/MSN-20990101-000000").status_code == 404
    assert client.get("/api/missions/not-an-id").status_code == 400


def test_metrics_reads_training_results(client, tmp_path):
    run = tmp_path / "runs" / "effnet_b0"
    (run / "baseline_comparison").mkdir(parents=True)
    (run / "results.json").write_text(json.dumps({"model": "efficientnet_b0", "accuracy": 0.88,
                                                  "history": [1, 2]}))
    (run / "baseline_comparison" / "comparison.json").write_text(json.dumps({"x": 1}))
    m = client.get("/api/metrics").json()
    assert m["models"][0]["accuracy"] == 0.88 and "history" not in m["models"][0]
    assert m["baseline_comparison"]["run"] == "effnet_b0"
