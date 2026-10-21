import pytest
from fastapi.testclient import TestClient
from app.auth import make_token
from app.main import app
from app.services import STATE

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_state():
    STATE.update(emergency=False, manual=None, mission_id=None)
    yield
    STATE.update(manual=None)


def _login(password="test-pass"):
    return client.post("/api/auth/login", json={"username": "operator", "password": password})


def test_wrong_password_is_rejected():
    assert _login("wrong").status_code == 401


def test_token_unlocks_control_endpoints():
    token = _login().json()["token"]
    r = client.post("/api/manual/OFF", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200 and r.json()["manual"] == "OFF"


def test_tampered_and_expired_tokens_are_rejected():
    token = _login().json()["token"]
    assert client.post("/api/manual/OFF", headers={"Authorization": f"Bearer {token[:-3]}xyz"}).status_code == 401
    expired = make_token("operator", ttl=-10)
    assert client.post("/api/manual/OFF", headers={"Authorization": f"Bearer {expired}"}).status_code == 401


def test_models_endpoint_reports_files():
    body = client.get("/api/models").json()
    assert "main_model" in body and "exists" in body["main_model"]