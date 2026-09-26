"""Forecast endpoints — tomorrow risk + bundled advice + history."""

from __future__ import annotations

from datetime import date as Date, timedelta
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.deps import get_current_user
from api.errors import api_error
from copilot.state import PatientAdviceType
from db.database import get_db
from db.models import User
from services.forecast_service import (
    ensure_card_predictions,
    get_forecast,
    list_forecasts,
    run_forecast,
)

router = APIRouter(tags=["forecast"])


class ForecastRequest(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    date: Optional[Date] = None
    llm_provider: Optional[Literal["claude", "gemini"]] = None
    advice_type: PatientAdviceType = "daily"
    timezone: str = Field("America/Chicago", description="IANA timezone for Google Calendar day bounds")
    calendar_events: Optional[list[dict[str, Any]]] = Field(
        None,
        description="Optional structured events override (skips Google fetch when provided)",
    )


class ForecastCardsRequest(BaseModel):
    """Home / Statistics card payload — get-or-create stored predictions."""

    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    llm_provider: Optional[Literal["claude", "gemini"]] = None
    advice_type: PatientAdviceType = "daily"
    timezone: str = Field("America/Chicago", description="IANA timezone for Google Calendar day bounds")


@router.post("/forecast")
async def create_forecast(
    body: ForecastRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return await run_forecast(
        db,
        user,
        lat=body.lat,
        lon=body.lon,
        anchor_date=body.date,
        llm_provider=body.llm_provider,
        advice_type=body.advice_type,
        calendar_events=body.calendar_events,
        timezone_name=body.timezone,
    )


@router.post("/forecasts/today")
async def ensure_today_forecasts(
    body: ForecastCardsRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Get-or-create predictions for the home/stats cards.

    Returns stored rows when present; otherwise runs ML + advice.
    Also backfills advice when a stored forecast has ``advice: null``.

    - ``today``: prediction targeting today (usually from yesterday's check-in)
    - ``tomorrow``: prediction targeting tomorrow (from today's check-in)
    """
    return await ensure_card_predictions(
        db,
        user,
        lat=body.lat,
        lon=body.lon,
        llm_provider=body.llm_provider,
        advice_type=body.advice_type,
        timezone_name=body.timezone,
    )


@router.get("/forecasts/today")
def get_today_forecast(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Read-only peek at stored card predictions (no ML/LLM). Prefer POST to ensure."""
    today = Date.today()
    tomorrow = today + timedelta(days=1)
    for_today = get_forecast(db, user.id, targeting=today)
    for_tomorrow = get_forecast(db, user.id, targeting=tomorrow)
    if for_today is None and for_tomorrow is None:
        raise api_error(
            404,
            "No prediction available yet. Complete a symptom check-in and run a forecast.",
            "FORECAST_NOT_FOUND",
        )
    return {"today": for_today, "tomorrow": for_tomorrow}


@router.get("/forecasts")
def get_forecasts(
    from_date: Optional[Date] = Query(None, alias="from"),
    to_date: Optional[Date] = Query(None, alias="to"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return {
        "items": list_forecasts(db, user.id, from_date=from_date, to_date=to_date),
    }
