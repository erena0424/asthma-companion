"""POST /v1/wearables/daily endpoint tests."""

from datetime import date, timedelta

from fastapi.testclient import TestClient


def test_ingest_wearable_daily(client: TestClient, auth_headers: dict):
    day = (date.today() - timedelta(days=1)).isoformat()
    response = client.post(
        "/v1/wearables/daily",
        json={
            "date": day,
            "sleep_minutes": 390,
            "total_steps": 6200,
            "sedentary_minutes": 480,
            "running_minutes": 15,
            "avg_hr": 71.0,
        },
        headers=auth_headers,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["date"] == day
    assert body["sleep_minutes"] == 390
    assert body["total_steps"] == 6200
    assert body["avg_hr"] == 71.0


def test_upsert_wearable_daily(client: TestClient, auth_headers: dict):
    day = (date.today() - timedelta(days=2)).isoformat()
    payload = {"date": day, "sleep_minutes": 400, "total_steps": 5000}
    assert client.post("/v1/wearables/daily", json=payload, headers=auth_headers).status_code == 201

    updated = client.post(
        "/v1/wearables/daily",
        json={"date": day, "sleep_minutes": 420, "total_steps": 5500},
        headers=auth_headers,
    )
    assert updated.status_code == 201
    assert updated.json()["sleep_minutes"] == 420
    assert updated.json()["total_steps"] == 5500


def test_wearables_requires_auth(client: TestClient):
    response = client.post("/v1/wearables/daily", json={"date": "2026-06-01", "sleep_minutes": 400})
    assert response.status_code == 401
