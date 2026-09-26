"""Forecast and advice API tests."""

from __future__ import annotations

from datetime import date
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import CheckIn, User


def test_forecast_requires_check_in_or_puff(client: TestClient, auth_headers: dict):
    response = client.post(
        "/v1/forecast",
        json={"lat": 42.36, "lon": -71.06},
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert response.json()["code"] == "CHECK_IN_REQUIRED"


@patch("services.forecast_service.generate_advice")
@patch("services.forecast_service.fetch_env_daily")
def test_forecast_with_puff_only(
    mock_fetch_env,
    mock_generate_advice,
    client: TestClient,
    auth_headers: dict,
    mock_env_fetch,
    mock_advice,
):
    mock_fetch_env.side_effect = mock_env_fetch.side_effect
    mock_generate_advice.side_effect = mock_advice.side_effect

    assert client.post("/v1/check-ins/inhaler/puff", headers=auth_headers).status_code == 200

    response = client.post(
        "/v1/forecast",
        json={"lat": 42.36, "lon": -71.06},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["prediction_mode"] == "classifier"
    assert "flare_probability" in body
    assert body["advice"]["summary"] == "Test advice summary."
    assert "data_quality" in body
    assert "calendar" in body["data_quality"]["unavailable_context"]


@patch("services.forecast_service.generate_advice")
@patch("services.forecast_service.fetch_env_daily")
def test_advice_regeneration(
    mock_fetch_env,
    mock_generate_advice,
    client: TestClient,
    auth_headers: dict,
    mock_env_fetch,
    mock_advice,
):
    mock_fetch_env.side_effect = mock_env_fetch.side_effect
    mock_generate_advice.side_effect = mock_advice.side_effect

    client.post("/v1/check-ins", json={}, headers=auth_headers)
    client.post("/v1/forecast", json={"lat": 42.36, "lon": -71.06}, headers=auth_headers)

    mock_generate_advice.reset_mock()
    mock_generate_advice.side_effect = mock_advice.side_effect

    advice = client.post("/v1/advice", json={"llm_provider": "gemini"}, headers=auth_headers)
    assert advice.status_code == 200, advice.text
    assert advice.json()["advice"]["summary"] == "Test advice summary."
    assert mock_generate_advice.called
    assert "check_in" not in advice.json()["data_quality"]["unavailable_context"]


@patch("services.forecast_service.generate_advice")
@patch("services.forecast_service.fetch_env_daily")
def test_advice_without_check_in_still_returns_advice(
    mock_fetch_env,
    mock_generate_advice,
    client: TestClient,
    auth_headers: dict,
    db_session: Session,
    mock_env_fetch,
    mock_advice,
):
    """Advice may run from cached forecast + environment even if today's check-in is gone."""
    mock_fetch_env.side_effect = mock_env_fetch.side_effect
    mock_generate_advice.side_effect = mock_advice.side_effect

    client.post(
        "/v1/check-ins",
        json={"calendar_event": "Outdoor walk"},
        headers=auth_headers,
    )
    forecast = client.post(
        "/v1/forecast",
        json={"lat": 42.36, "lon": -71.06},
        headers=auth_headers,
    )
    assert forecast.status_code == 200, forecast.text

    user = db_session.scalar(select(User).where(User.email == "testuser@example.com"))
    assert user is not None
    check_in = db_session.scalar(
        select(CheckIn).where(CheckIn.user_id == user.id, CheckIn.date == date.today())
    )
    assert check_in is not None
    db_session.delete(check_in)
    db_session.commit()

    mock_generate_advice.reset_mock()
    mock_generate_advice.side_effect = mock_advice.side_effect

    advice = client.post("/v1/advice", json={}, headers=auth_headers)
    assert advice.status_code == 200, advice.text
    body = advice.json()
    assert body["advice"]["summary"] == "Test advice summary."
    assert "check_in" in body["data_quality"]["unavailable_context"]
    assert any("without today's symptom check-in" in w for w in body["warnings"])

    kwargs = mock_generate_advice.call_args.kwargs
    assert "unknown" in kwargs["symptoms_summary"].lower()
    assert kwargs["calendar_event"] is None


def test_advice_without_forecast_returns_404(client: TestClient, auth_headers: dict):
    response = client.post("/v1/advice", json={}, headers=auth_headers)
    assert response.status_code == 404
    assert response.json()["code"] == "FORECAST_NOT_FOUND"


@patch("services.forecast_service.generate_advice")
@patch("services.forecast_service.fetch_env_daily")
def test_forecast_survives_llm_outage(
    mock_fetch_env,
    mock_generate_advice,
    client: TestClient,
    auth_headers: dict,
    mock_env_fetch,
):
    mock_fetch_env.side_effect = mock_env_fetch.side_effect
    mock_generate_advice.side_effect = RuntimeError("provider outage")
    assert client.post("/v1/check-ins", json={}, headers=auth_headers).status_code == 201

    response = client.post(
        "/v1/forecast",
        json={"lat": 42.36, "lon": -71.06},
        headers=auth_headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["advice"] is None
    assert any("forecast is still valid" in warning for warning in response.json()["warnings"])


@patch("services.forecast_service.generate_advice")
@patch("services.forecast_service.fetch_env_daily")
def test_forecast_reuse_backfills_missing_advice(
    mock_fetch_env,
    mock_generate_advice,
    client: TestClient,
    auth_headers: dict,
    mock_env_fetch,
    mock_advice,
):
    """If the first run stored ML without advice, a later POST fills advice in."""
    mock_fetch_env.side_effect = mock_env_fetch.side_effect
    mock_generate_advice.side_effect = RuntimeError("provider outage")
    assert client.post("/v1/check-ins", json={}, headers=auth_headers).status_code == 201

    first = client.post(
        "/v1/forecast",
        json={"lat": 42.36, "lon": -71.06},
        headers=auth_headers,
    )
    assert first.status_code == 200, first.text
    assert first.json()["advice"] is None
    probability = first.json()["flare_probability"]

    mock_generate_advice.reset_mock()
    mock_generate_advice.side_effect = mock_advice.side_effect

    second = client.post(
        "/v1/forecast",
        json={"lat": 42.36, "lon": -71.06},
        headers=auth_headers,
    )
    assert second.status_code == 200, second.text
    assert second.json()["advice"]["summary"] == "Test advice summary."
    assert second.json()["flare_probability"] == probability
    assert mock_generate_advice.called


@patch("services.forecast_service.generate_advice")
@patch("services.forecast_service.fetch_env_daily")
def test_forecast_passes_manual_calendar_event(
    mock_fetch_env,
    mock_generate_advice,
    client: TestClient,
    auth_headers: dict,
    mock_env_fetch,
    mock_advice,
):
    from datetime import date, timedelta

    mock_fetch_env.side_effect = mock_env_fetch.side_effect
    mock_generate_advice.side_effect = mock_advice.side_effect

    today = date.today()
    tomorrow = today + timedelta(days=1)
    assert (
        client.post(
            "/v1/check-ins",
            json={"date": today.isoformat()},
            headers=auth_headers,
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/v1/check-ins",
            json={
                "date": tomorrow.isoformat(),
                "calendar_event": "Outdoor soccer tomorrow",
            },
            headers=auth_headers,
        ).status_code
        == 201
    )
    response = client.post(
        "/v1/forecast",
        json={"lat": 42.36, "lon": -71.06},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    kwargs = mock_generate_advice.call_args.kwargs
    assert kwargs["calendar_event"] == "Outdoor soccer tomorrow"
    assert kwargs["calendar_events"]
    assert kwargs["calendar_events"][0]["title"] == "Outdoor soccer tomorrow"
    assert kwargs["calendar_events"][0]["source"] == "manual"
    assert "calendar" not in response.json()["data_quality"]["unavailable_context"]


@patch("services.forecast_service.generate_advice")
@patch("services.forecast_service.fetch_env_daily")
def test_same_day_calendar_text_feeds_today_card_advice(
    mock_fetch_env,
    mock_generate_advice,
    client: TestClient,
    auth_headers: dict,
    mock_env_fetch,
    mock_advice,
    db_session,
):
    """Free-text on today's check-in should reach advice for today's prediction card."""
    from datetime import date, timedelta

    mock_fetch_env.side_effect = mock_env_fetch.side_effect
    mock_generate_advice.side_effect = mock_advice.side_effect

    today = date.today()
    yesterday = today - timedelta(days=1)

    assert (
        client.post(
            "/v1/check-ins",
            json={"date": yesterday.isoformat(), "daily_day_symp": False},
            headers=auth_headers,
        ).status_code
        == 201
    )
    # Build today's card (from yesterday's check-in) first.
    first = client.post(
        "/v1/forecast",
        json={"lat": 42.36, "lon": -71.06, "date": yesterday.isoformat()},
        headers=auth_headers,
    )
    assert first.status_code == 200, first.text

    # Demo path: add calendar text on today without Google.
    assert (
        client.post(
            "/v1/check-ins",
            json={"date": today.isoformat(), "calendar_event": "Ice skating"},
            headers=auth_headers,
        ).status_code
        == 201
    )

    mock_generate_advice.reset_mock()
    mock_generate_advice.side_effect = mock_advice.side_effect
    advice = client.post("/v1/advice", json={}, headers=auth_headers)
    assert advice.status_code == 200, advice.text
    kwargs = mock_generate_advice.call_args.kwargs
    assert kwargs["calendar_event"] == "Ice skating"
    assert any(
        isinstance(e, dict) and e.get("title") == "Ice skating"
        for e in (kwargs.get("calendar_events") or [])
    )


@patch("services.forecast_service.generate_advice")
@patch("services.forecast_service.fetch_env_daily")
def test_yesterdays_calendar_text_does_not_apply_to_today(
    mock_fetch_env,
    mock_generate_advice,
    client: TestClient,
    auth_headers: dict,
    mock_env_fetch,
    mock_advice,
):
    """Ice skating on yesterday's check-in must not show up as today's plan."""
    from datetime import date, timedelta

    mock_fetch_env.side_effect = mock_env_fetch.side_effect
    mock_generate_advice.side_effect = mock_advice.side_effect

    today = date.today()
    yesterday = today - timedelta(days=1)

    assert (
        client.post(
            "/v1/check-ins",
            json={"date": yesterday.isoformat(), "calendar_event": "Ice skating"},
            headers=auth_headers,
        ).status_code
        == 201
    )
    response = client.post(
        "/v1/forecast",
        json={"lat": 42.36, "lon": -71.06, "date": yesterday.isoformat()},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    kwargs = mock_generate_advice.call_args.kwargs
    events = kwargs.get("calendar_events") or []
    assert not any(
        isinstance(event, dict) and "ice skating" in str(event.get("title") or "").lower()
        for event in events
    )
    assert kwargs.get("calendar_event") in (None, "")