"""Wearable daily aggregate ingestion."""

from __future__ import annotations

from datetime import date as Date
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.deps import get_current_user
from db.database import get_db
from db.models import User, WearableDaily

router = APIRouter(prefix="/wearables", tags=["wearables"])


class WearableDailyInput(BaseModel):
    date: Date
    sleep_minutes: Optional[int] = Field(None, ge=0)
    total_steps: Optional[int] = Field(None, ge=0)
    sedentary_minutes: Optional[int] = Field(None, ge=0)
    running_minutes: Optional[int] = Field(None, ge=0)
    avg_hr: Optional[float] = Field(None, ge=0)


@router.post("/daily", status_code=201)
def ingest_wearable_daily(
    body: WearableDailyInput,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    row = db.scalar(
        select(WearableDaily).where(WearableDaily.user_id == user.id, WearableDaily.date == body.date)
    )
    if row is None:
        row = WearableDaily(user_id=user.id, date=body.date)
        db.add(row)

    row.sleep_minutes = body.sleep_minutes
    row.total_steps = body.total_steps
    row.sedentary_minutes = body.sedentary_minutes
    row.running_minutes = body.running_minutes
    row.avg_hr = body.avg_hr
    db.commit()
    db.refresh(row)

    return {
        "date": row.date.isoformat(),
        "sleep_minutes": row.sleep_minutes,
        "total_steps": row.total_steps,
        "sedentary_minutes": row.sedentary_minutes,
        "running_minutes": row.running_minutes,
        "avg_hr": row.avg_hr,
    }
