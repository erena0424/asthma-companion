"""Live integration tests — hit real OpenWeather, Google Pollen, and LLM APIs.

These are opt-in so the default test suite stays fast and does not require keys.

Run:
  RUN_LIVE_API_TESTS=1 pytest -m live -v
  ./run_live_tests.sh
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from model.elena_env_schema import ENV_FEATURE_COLUMNS, POLLEN_LEVELS
from tests.conftest import env_key_set

pytestmark = [pytest.mark.live, pytest.mark.usefixtures("require_live_api")]

BOSTON = {"lat": 42.36, "lon": -71.06}


def _assert_env_features(body: dict, *, require_no: bool = False) -> None:
    assert body["provider"] == "openweather"
    features = body["features"]
    missing = set(body.get("missing", []))
    for col in ENV_FEATURE_COLUMNS:
        assert col in features, f"missing column {col}"
        if col in missing:
            continue
        assert features[col] is not None, f"null value for {col}"
    for col in ("grass_pollen", "tree_pollen", "weed_pollen"):
        assert features[col] in POLLEN_LEVELS
    assert isinstance(body["missing"], list)
    if require_no:
        assert "no" not in missing
        assert features["no"] is not None


def test_live_env_openweather(client: TestClient):
    if not env_key_set("OPENWEATHER_API_KEY"):
        pytest.skip("OPENWEATHER_API_KEY not set in .env")

    response = client.get(
        "/v1/env/daily",
        params={**BOSTON, "provider": "openweather"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["provider"] == "openweather"
    _assert_env_features(body, require_no=True)


def test_live_env_default_provider(client: TestClient):
    """Uses ENV_PROVIDER from .env (expected: openweather in production)."""
    provider = os.getenv("ENV_PROVIDER", "openweather")
    if provider == "openweather" and not env_key_set("OPENWEATHER_API_KEY"):
        pytest.skip("ENV_PROVIDER=openweather but OPENWEATHER_API_KEY missing")

    response = client.get("/v1/env/daily", params=BOSTON)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["provider"] == provider
    _assert_env_features(body, require_no=True)


def test_live_forecast_with_real_env_and_llm(client: TestClient, auth_headers: dict):
    provider = os.getenv("ENV_PROVIDER", "openweather")
    if provider == "openweather" and not env_key_set("OPENWEATHER_API_KEY"):
        pytest.skip("ENV_PROVIDER=openweather but OPENWEATHER_API_KEY missing")

    llm = os.getenv("LLM_PROVIDER", "gemini").lower()
    if llm == "gemini" and not env_key_set("GEMINI_API_KEY"):
        pytest.skip("LLM_PROVIDER=gemini but GEMINI_API_KEY missing")
    if llm == "claude" and not env_key_set("ANTHROPIC_API_KEY"):
        pytest.skip("LLM_PROVIDER=claude but ANTHROPIC_API_KEY missing")

    assert client.post("/v1/check-ins/inhaler/puff", headers=auth_headers).status_code == 200

    response = client.post(
        "/v1/forecast",
        json={**BOSTON, "llm_provider": llm},
        headers=auth_headers,
        timeout=120.0,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["prediction_mode"] == "classifier"
    assert isinstance(body["flare_probability"], float)
    assert body["risk_level"] in ("Low", "Medium", "High")
    assert body["advice"]["summary"]
    assert body["advice"]["summary"] != "Test advice summary."
    assert len(body["advice"]["sections"]) >= 1
    assert body["advice"]["llm_provider"] == llm


def test_live_advice_regeneration(client: TestClient, auth_headers: dict):
    provider = os.getenv("ENV_PROVIDER", "openweather")
    if provider == "openweather" and not env_key_set("OPENWEATHER_API_KEY"):
        pytest.skip("ENV_PROVIDER=openweather but OPENWEATHER_API_KEY missing")

    llm = os.getenv("LLM_PROVIDER", "gemini").lower()
    if llm == "gemini" and not env_key_set("GEMINI_API_KEY"):
        pytest.skip("GEMINI_API_KEY missing")
    if llm == "claude" and not env_key_set("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY missing")

    client.post("/v1/check-ins/inhaler/puff", headers=auth_headers)
    forecast = client.post(
        "/v1/forecast",
        json={**BOSTON, "llm_provider": llm},
        headers=auth_headers,
        timeout=120.0,
    )
    assert forecast.status_code == 200, forecast.text
    first_summary = forecast.json()["advice"]["summary"]

    advice = client.post(
        "/v1/advice",
        json={"llm_provider": llm},
        headers=auth_headers,
        timeout=120.0,
    )
    assert advice.status_code == 200, advice.text
    second_summary = advice.json()["advice"]["summary"]
    assert second_summary
    assert second_summary != "Test advice summary."
    # LLM output may match; both must be non-empty real strings
    assert len(first_summary) > 10
    assert len(second_summary) > 10
