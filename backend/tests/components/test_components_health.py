import pytest
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


@pytest.mark.parametrize(
    "prefix, name",
    [
        ("c1", "c1_spray_detection"),
        ("c2", "c2_wind_handling"),
        ("c3", "c3_smart_path"),
        ("c4", "c4_maturity"),
    ],
)
def test_component_health(prefix, name):
    response = client.get(f"/api/{prefix}/health")
    assert response.status_code == 200
    assert response.json() == {"component": name, "status": "ok"}