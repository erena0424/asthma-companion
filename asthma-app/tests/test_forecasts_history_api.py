"""GET /v1/forecasts history tests."""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import patch

from fastapi.testclient import TestClient


def _check_in(client: TestClient, headers: dict, day: str) -> None:
    client.post(
        "/v1/check-ins",
        json={
            "date": day,
            "daily_day_symp": True,
            "daily_night_symp": False,
            "daily_limit_activity": False,
            "puffs_today": 1,
        },
        headers=headers,
    )


@patch("services.forecast_service.generate_advice")
@patch("services.forecast_service.fetch_env_daily")
def test_list_and_get_today_forecast_from_yesterday(
    mock_fetch_env,
    mock_generate_advice,
    client: TestClient,
    auth_headers: dict,
    mock_env_fetch,
    mock_advice,
):
    mock_fetch_env.side_effect = mock_env_fetch.side_effect
    mock_generate_advice.side_effect = mock_advice.side_effect

    yesterday = (date.today() - timedelta(days=1)).isoformat()
    _check_in(client, auth_headers, yesterday)
    create = client.post(
        "/v1/forecast",
        json={"lat": 42.36, "lon": -71.06, "date": yesterday},
        headers=auth_headers,
    )
    assert create.status_code == 200, create.text
    assert create.json()["forecast_for"] == date.today().isoformat()

    today = client.get("/v1/forecasts/today", headers=auth_headers)
    assert today.status_code == 200, today.text
    payload = today.json()
    assert payload["today"] is not None
    assert payload["today"]["forecast_for"] == date.today().isoformat()
    assert payload["tomorrow"] is None

    history = client.get("/v1/forecasts", headers=auth_headers)
    assert history.status_code == 200
    assert len(history.json()["items"]) >= 1


@patch("services.forecast_service.generate_advice")
@patch("services.forecast_service.fetch_env_daily")
def test_forecast_is_stored_and_reused(
    mock_fetch_env,
    mock_generate_advice,
    client: TestClient,
    auth_headers: dict,
    mock_env_fetch,
    mock_advice,
):
    mock_fetch_env.side_effect = mock_env_fetch.side_effect
    mock_generate_advice.side_effect = mock_advice.side_effect

    yesterday = (date.today() - timedelta(days=1)).isoformat()
    _check_in(client, auth_headers, yesterday)

    first = client.post(
        "/v1/forecast",
        json={"lat": 42.36, "lon": -71.06, "date": yesterday},
        headers=auth_headers,
    )
    assert first.status_code == 200, first.text
    first_prob = first.json()["flare_probability"]

    second = client.post(
        "/v1/forecast",
        json={"lat": 42.36, "lon": -71.06, "date": yesterday},
        headers=auth_headers,
    )
    assert second.status_code == 200, second.text
    assert second.json()["flare_probability"] == first_prob
    # Second call should reuse the stored row (no second advice generation).
    assert mock_generate_advice.call_count == 1


@patch("services.forecast_service.generate_advice")
@patch("services.forecast_service.fetch_env_daily")
def test_forecasts_today_includes_tomorrow_when_run_today(
    mock_fetch_env,
    mock_generate_advice,
    client: TestClient,
    auth_headers: dict,
    mock_env_fetch,
    mock_advice,
):
    mock_fetch_env.side_effect = mock_env_fetch.side_effect
    mock_generate_advice.side_effect = mock_advice.side_effect

    yesterday = (date.today() - timedelta(days=1)).isoformat()
    today = date.today().isoformat()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()

    _check_in(client, auth_headers, yesterday)
    client.post(
        "/v1/forecast",
        json={"lat": 42.36, "lon": -71.06, "date": yesterday},
        headers=auth_headers,
    )

    _check_in(client, auth_headers, today)
    client.post(
        "/v1/forecast",
        json={"lat": 42.36, "lon": -71.06},
        headers=auth_headers,
    )

    card = client.get("/v1/forecasts/today", headers=auth_headers)
    assert card.status_code == 200, card.text
    payload = card.json()
    assert payload["today"]["forecast_for"] == today
    assert payload["tomorrow"]["forecast_for"] == tomorrow


def test_forecasts_today_without_run_returns_404(client: TestClient, auth_headers: dict):
    response = client.get("/v1/forecasts/today", headers=auth_headers)
    assert response.status_code == 404
    assert response.json()["code"] == "FORECAST_NOT_FOUND"


@patch("services.forecast_service.generate_advice")
@patch("services.forecast_service.fetch_env_daily")
def test_post_forecasts_today_get_or_creates(
    mock_fetch_env,
    mock_generate_advice,
    client: TestClient,
    auth_headers: dict,
    mock_env_fetch,
    mock_advice,
):
    """POST /v1/forecasts/today calculates when nothing is stored."""
    mock_fetch_env.side_effect = mock_env_fetch.side_effect
    mock_generate_advice.side_effect = mock_advice.side_effect

    yesterday = (date.today() - timedelta(days=1)).isoformat()
    _check_in(client, auth_headers, yesterday)

    first = client.post(
        "/v1/forecasts/today",
        json={"lat": 42.36, "lon": -71.06},
        headers=auth_headers,
    )
    assert first.status_code == 200, first.text
    payload = first.json()
    assert payload["today"] is not None
    assert payload["today"]["forecast_for"] == date.today().isoformat()
    assert payload["today"]["advice"]["summary"] == "Test advice summary."
    assert mock_generate_advice.call_count == 1

    mock_generate_advice.reset_mock()
    second = client.post(
        "/v1/forecasts/today",
        json={"lat": 42.36, "lon": -71.06},
        headers=auth_headers,
    )
    assert second.status_code == 200, second.text
    assert second.json()["today"]["flare_probability"] == payload["today"]["flare_probability"]
    # Stored row reused — no second ML/advice run when advice is already present.
    assert mock_generate_advice.call_count == 0


@patch("services.forecast_service.generate_advice")
@patch("services.forecast_service.fetch_env_daily")
def test_post_forecasts_today_backfills_missing_advice(
    mock_fetch_env,
    mock_generate_advice,
    client: TestClient,
    auth_headers: dict,
    mock_env_fetch,
    mock_advice,
):
    mock_fetch_env.side_effect = mock_env_fetch.side_effect
    mock_generate_advice.side_effect = RuntimeError("provider outage")

    yesterday = (date.today() - timedelta(days=1)).isoformat()
    _check_in(client, auth_headers, yesterday)
    first = client.post(
        "/v1/forecast",
        json={"lat": 42.36, "lon": -71.06, "date": yesterday},
        headers=auth_headers,
    )
    assert first.status_code == 200
    assert first.json()["advice"] is None

    mock_generate_advice.reset_mock()
    mock_generate_advice.side_effect = mock_advice.side_effect

    cards = client.post(
        "/v1/forecasts/today",
        json={"lat": 42.36, "lon": -71.06},
        headers=auth_headers,
    )
    assert cards.status_code == 200, cards.text
    assert cards.json()["today"]["advice"]["summary"] == "Test advice summary."
    assert mock_generate_advice.called


def test_post_forecasts_today_without_check_in_returns_404(
    client: TestClient, auth_headers: dict
):
    response = client.post(
        "/v1/forecasts/today",
        json={"lat": 42.36, "lon": -71.06},
        headers=auth_headers,
    )
    assert response.status_code == 404
    assert response.json()["code"] == "FORECAST_NOT_FOUND"
