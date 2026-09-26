"""Regenerate advice from a cached forecast without re-running the classifier."""

from __future__ import annotations

from datetime import date as Date
from typing import Literal, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.deps import get_current_user
from copilot.state import PatientAdviceType
from db.database import get_db
from db.models import User
from services.forecast_service import regenerate_advice

router = APIRouter(prefix="/advice", tags=["advice"])


class AdviceRequest(BaseModel):
    date: Optional[Date] = None
    llm_provider: Optional[Literal["claude", "gemini"]] = None
    advice_type: PatientAdviceType = "daily"


@router.post("")
async def create_advice(
    body: AdviceRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return await regenerate_advice(
        db,
        user,
        anchor_date=body.date,
        llm_provider=body.llm_provider,
        advice_type=body.advice_type,
    )
