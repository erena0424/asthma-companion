"""Chat Q&A over a cached forecast via the shared Copilot LangGraph."""

from __future__ import annotations

from datetime import date as Date
from typing import Literal, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.deps import get_current_user
from db.database import get_db
from db.models import User
from services.forecast_service import generate_chat_reply

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    date: Optional[Date] = None
    llm_provider: Optional[Literal["claude", "gemini"]] = None


@router.post("/chat")
async def create_chat(
    body: ChatRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Answer a user message using Copilot context. Does not overwrite Forecast.advice."""
    return await generate_chat_reply(
        db,
        user,
        message=body.message,
        anchor_date=body.date,
        llm_provider=body.llm_provider,
    )
