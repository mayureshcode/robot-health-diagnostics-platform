"""FastAPI contract tests, isolated from the ROS graph by injected store."""

from fastapi.testclient import TestClient
import pytest

from rhm_dashboard.schema import HealthStore
from rhm_dashboard.server import create_app


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Create authenticated API that does not start a ROS thread."""
    monkeypatch.setenv("RHM_DASHBOARD_TOKEN", "test-secret-for-tests")
    monkeypatch.setenv("RHM_DASHBOARD_DISABLE_ROS", "1")
    return TestClient(create_app(HealthStore()))


def test_healthz_is_not_robot_health(client: TestClient) -> None:
    """Readiness endpoint must not claim robot connectivity."""
    assert client.get("/api/healthz").json() == {"api": "ready", "robot_health": "not_checked"}


def test_api_requires_bearer(client: TestClient) -> None:
    """External requests without token cannot read telemetry."""
    assert client.get("/api/snapshot").status_code == 401
    assert client.get("/api/snapshot", headers={"Authorization": "Bearer wrong"}).status_code == 401
    response = client.get("/api/snapshot", headers={"Authorization": "Bearer test-secret-for-tests"})
    assert response.status_code == 200
    assert response.json()["health_score"] is None
    assert response.json()["received_health"] is False


def test_websocket_requires_token(client: TestClient) -> None:
    """WebSocket sends no health data before successful first-message auth."""
    with client.websocket_connect("/ws/health") as ws:
        ws.send_json({"token": "test-secret-for-tests"})
        payload = ws.receive_json()
        assert payload["type"] == "snapshot"
        assert payload["data"]["health_score"] is None


def test_never_accept_public_binding_without_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    """Public bind with no token is an explicit configuration error."""
    monkeypatch.delenv("RHM_DASHBOARD_TOKEN", raising=False)
    monkeypatch.setenv("RHM_DASHBOARD_HOST", "0.0.0.0")
    with pytest.raises(RuntimeError):
        create_app()
