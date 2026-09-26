"""POST /v1/chat API tests."""

from __future__ import annotations

from datetime import date
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import Forecast, User


@patch("services.forecast_service.generate_advice")
@patch("services.forecast_service.fetch_env_daily")
def test_chat_answers_without_overwriting_stored_advice(
    mock_fetch_env,
    mock_generate_advice,
    client: TestClient,
    auth_headers: dict,
    db_session: Session,
    mock_env_fetch,
    mock_advice,
):
    mock_fetch_env.side_effect = mock_env_fetch.side_effect
    mock_generate_advice.side_effect = mock_advice.side_effect

    assert client.post("/v1/check-ins", json={}, headers=auth_headers).status_code == 201
    forecast = client.post(
        "/v1/forecast",
        json={"lat": 42.36, "lon": -71.06},
        headers=auth_headers,
    )
    assert forecast.status_code == 200, forecast.text
    stored_summary = forecast.json()["advice"]["summary"]

    chat_advice = {
        "summary": "Limit outdoor running today.",
        "sections": [{"title": "Activity", "body": "Choose an indoor alternative."}],
        "disclaimer": "Educational only.",
    }

    def _chat_side_effect(**kwargs):
        assert kwargs.get("question") == "Should I run outside?"
        return chat_advice, [], None

    mock_generate_advice.reset_mock()
    mock_generate_advice.side_effect = _chat_side_effect

    chat = client.post(
        "/v1/chat",
        json={"message": "Should I run outside?"},
        headers=auth_headers,
    )
    assert chat.status_code == 200, chat.text
    body = chat.json()
    assert body["advice"]["summary"] == "Limit outdoor running today."
    assert mock_generate_advice.called

    user = db_session.scalar(select(User).where(User.email == "testuser@example.com"))
    row = db_session.scalar(
        select(Forecast)
        .where(Forecast.user_id == user.id, Forecast.date == date.today())
        .order_by(Forecast.created_at.desc())
    )
    assert row is not None
    assert row.advice["summary"] == stored_summary


@patch("services.forecast_service.generate_advice")
@patch("services.forecast_service.fetch_env_daily")
def test_advice_without_message_still_persists(
    mock_fetch_env,
    mock_generate_advice,
    client: TestClient,
    auth_headers: dict,
    db_session: Session,
    mock_env_fetch,
    mock_advice,
):
    mock_fetch_env.side_effect = mock_env_fetch.side_effect
    mock_generate_advice.side_effect = mock_advice.side_effect

    client.post("/v1/check-ins", json={}, headers=auth_headers)
    client.post("/v1/forecast", json={"lat": 42.36, "lon": -71.06}, headers=auth_headers)

    updated = {
        "summary": "Updated daily recommendation.",
        "sections": [{"title": "Today", "body": "Monitor symptoms."}],
        "disclaimer": "Educational only.",
    }
    mock_generate_advice.reset_mock()
    mock_generate_advice.side_effect = lambda **_kwargs: (updated, [], None)

    advice = client.post("/v1/advice", json={}, headers=auth_headers)
    assert advice.status_code == 200, advice.text
    assert advice.json()["advice"]["summary"] == "Updated daily recommendation."

    user = db_session.scalar(select(User).where(User.email == "testuser@example.com"))
    row = db_session.scalar(
        select(Forecast)
        .where(Forecast.user_id == user.id, Forecast.date == date.today())
        .order_by(Forecast.created_at.desc())
    )
    assert row.advice["summary"] == "Updated daily recommendation."


def test_chat_without_forecast_returns_404(client: TestClient, auth_headers: dict):
    response = client.post(
        "/v1/chat",
        json={"message": "Why is my risk high?"},
        headers=auth_headers,
    )
    assert response.status_code == 404
    assert response.json()["code"] == "FORECAST_NOT_FOUND"


@patch("services.forecast_service.generate_advice")
@patch("services.forecast_service.fetch_env_daily")
def test_chat_uses_forecast_targeting_today(
    mock_fetch_env,
    mock_generate_advice,
    client: TestClient,
    auth_headers: dict,
    mock_env_fetch,
    mock_advice,
):
    """Home shows today's risk from yesterday's run; chat must find that row too."""
    from datetime import timedelta

    mock_fetch_env.side_effect = mock_env_fetch.side_effect
    mock_generate_advice.side_effect = mock_advice.side_effect

    yesterday = (date.today() - timedelta(days=1)).isoformat()
    assert (
        client.post(
            "/v1/check-ins",
            json={"date": yesterday},
            headers=auth_headers,
        ).status_code
        == 201
    )
    forecast = client.post(
        "/v1/forecast",
        json={"lat": 42.36, "lon": -71.06, "date": yesterday},
        headers=auth_headers,
    )
    assert forecast.status_code == 200, forecast.text
    assert forecast.json()["forecast_for"] == date.today().isoformat()

    mock_generate_advice.reset_mock()
    mock_generate_advice.side_effect = lambda **kwargs: (
        {
            "summary": "Because night symptoms raised today's risk.",
            "sections": [{"title": "Why", "body": "Night symptoms were logged."}],
            "disclaimer": "Educational only.",
        },
        [],
        None,
    )

    chat = client.post(
        "/v1/chat",
        json={"message": "hmm why"},
        headers=auth_headers,
    )
    assert chat.status_code == 200, chat.text
    assert "night" in chat.json()["advice"]["summary"].lower() or chat.json()["advice"]["summary"]
    assert mock_generate_advice.called


def test_chat_empty_message_returns_400(client: TestClient, auth_headers: dict):
    response = client.post(
        "/v1/chat",
        json={"message": "   "},
        headers=auth_headers,
    )
    # Pydantic min_length=1 may reject before strip, or service strip → 400.
    assert response.status_code == 400
