from fastapi.testclient import TestClient


def test_health_returns_expected_payload(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "revenue-recovery-orchestrator",
    }


def test_agent_health_is_degraded_safe(client: TestClient) -> None:
    response = client.get("/api/v1/agent/health")
    assert response.status_code == 200
    body = response.json()
    assert body["fallback_available"] is True
    assert "configured_mode" in body
    core = client.get("/health")
    assert core.status_code == 200
    assert core.json()["status"] == "healthy"
