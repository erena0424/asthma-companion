"""Authenticated supportive companion; no writes or emergency classification."""
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator
from sqlalchemy.orm import Session

from api.deps import get_current_user
from db.database import get_db
from db.models import User
from services.companion_service import reply

router = APIRouter(prefix="/companion", tags=["companion"])


class CompanionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(min_length=1, max_length=1000)
    include_saved_context: StrictBool = False
    persona: Literal["warm", "calm", "direct"] = "warm"

    @field_validator("message")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Message cannot be blank")
        return value.strip()


@router.post("/chat")
async def companion_chat(body: CompanionRequest,
                         user: User = Depends(get_current_user),
                         db: Session = Depends(get_db)):
    return await reply(db, user, body.message,
                       include_saved_context=body.include_saved_context, persona=body.persona)
