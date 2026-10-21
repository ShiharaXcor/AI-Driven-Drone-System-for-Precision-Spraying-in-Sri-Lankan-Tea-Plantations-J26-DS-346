import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.settings_store import reset_settings

client = TestClient(app)
KEY = {"x-api-key": "dev-key"}


@pytest.fixture(autouse=True)
def clean():
    reset_settings()
    yield
    reset_settings()


def test_defaults_are_returned():
    assert client.get("/api/settings").json()["current"]["person_stop"] == 0.30


def test_update_changes_the_decision():
    tea = {"detections": [{"cls": "tea_plant", "conf": 0.9}]}
    assert client.post("/api/decide", json=tea).json()["decision"] == "SPRAY"
    assert client.put("/api/settings", json={"tea_spray": 0.95}, headers=KEY).status_code == 200
    assert client.post("/api/decide", json=tea).json()["decision"] == "UNCERTAIN"


def test_requires_key():
    assert client.put("/api/settings", json={"tea_spray": 0.8}).status_code == 401


@pytest.mark.parametrize("body", [
    {"nonsense": 0.5},                        # unknown key
    {"tea_spray": 1.5},                       # out of range
    {"person_stop": 0.1},                     # stop below uncertain (0.15)
    {"person_stop": 0.9},                     # unsafe: above the safety limit
])
def test_bad_values_are_rejected(body):
    assert client.put("/api/settings", json=body, headers=KEY).status_code == 400