"""Authenticated supportive companion; no writes or emergency classification."""
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator, model_validator
from sqlalchemy.orm import Session

from api.deps import get_current_user
from db.database import get_db
from db.models import User
from services.companion_service import reply

router = APIRouter(prefix="/companion", tags=["companion"])


class HistoryMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=1200)

    @field_validator("content")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("History cannot be blank")
        return value.strip()


class CompanionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(min_length=1, max_length=1000)
    include_saved_context: StrictBool = True
    persona: Literal["warm", "calm", "direct"] = "warm"

    opening_message: str | None = Field(default=None, max_length=1200)
    history: list[HistoryMessage] = Field(default_factory=list, max_length=8)
    context_token: str | None = Field(default=None, max_length=64)

    @model_validator(mode="after")
    def bounded_exchanges(self):
        if len(self.history) % 2 or any(item.role != ("user" if i % 2 == 0 else "assistant")
                                       for i, item in enumerate(self.history)):
            raise ValueError("History must contain complete user/assistant exchanges")
        if sum(len(item.content) for item in self.history) > 6000:
            raise ValueError("History exceeds budget")
        return self

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
                       include_saved_context=body.include_saved_context, persona=body.persona,
                       history=[item.model_dump() for item in body.history], context_token=body.context_token,
                       opening_message=body.opening_message)


class OpeningRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    include_saved_context: StrictBool = True
    persona: Literal["warm", "calm", "direct"] = "warm"


@router.post("/opening")
async def companion_opening(body: OpeningRequest,
                            user: User = Depends(get_current_user),
                            db: Session = Depends(get_db)):
    return await reply(db, user, None, opening=True,
                       include_saved_context=body.include_saved_context, persona=body.persona)
