"""Health endpoint tests."""

from fastapi.testclient import TestClient


def test_health_includes_database_status(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert "database" in body
    assert "connected" in body["database"]
    assert body["database"]["connected"] is True
    assert body["status"] in ("ok", "degraded")
