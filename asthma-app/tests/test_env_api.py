"""GET /v1/env/daily endpoint tests (mocked provider — no API keys required)."""

from unittest.mock import patch

from fastapi.testclient import TestClient


@patch("api.env.fetch_env_daily")
def test_env_daily_returns_elena_features(mock_fetch, client: TestClient, mock_env_fetch):
    mock_fetch.side_effect = mock_env_fetch.side_effect

    response = client.get("/v1/env/daily", params={"lat": 42.36, "lon": -71.06, "provider": "openmeteo"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["lat"] == 42.36
    assert body["lon"] == -71.06
    assert body["provider"] == "openmeteo"
    assert "temperature" in body["features"]
    assert "grass_pollen" in body["features"]
    assert isinstance(body["missing"], list)


@patch("api.env.fetch_env_daily")
def test_env_daily_invalid_provider_returns_400(mock_fetch, client: TestClient):
    mock_fetch.side_effect = ValueError("Unknown provider 'bad'")

    response = client.get("/v1/env/daily", params={"lat": 42.36, "lon": -71.06, "provider": "bad"})
    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"


@patch("api.env.fetch_env_daily")
def test_env_daily_provider_failure_returns_api_error(mock_fetch, client: TestClient):
    mock_fetch.side_effect = RuntimeError("Open-Meteo request failed")

    response = client.get("/v1/env/daily", params={"lat": 42.36, "lon": -71.06, "provider": "openweather"})
    assert response.status_code == 502
    body = response.json()
    assert body["code"] == "ENV_PROVIDER_ERROR"
    assert "Environment provider error" in body["detail"]
