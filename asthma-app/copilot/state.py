"""Typed contracts shared by Copilot providers and LangGraph nodes."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import NotRequired, TypedDict

AdviceType = Literal[
    "daily",
    "emergency",
    "action_plan",
    "air_quality",
    "wildfire",
    "adherence",
    "exercise",
    "clinical_reference",
]
PatientAdviceType = Literal[
    "daily",
    "emergency",
    "action_plan",
    "air_quality",
    "wildfire",
    "adherence",
    "exercise",
]
KnowledgeAudience = Literal["patient", "clinician"]


class CalendarEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=300)
    start: datetime | date
    end: datetime | date | None = None
    source: str = "calendar"
    location: str | None = None
    description: str | None = None
    all_day: bool = False


class HistoricalEpisode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: date
    events: list[str] = Field(default_factory=list)
    environment: dict[str, Any] = Field(default_factory=dict)
    sleep_minutes: int | None = None
    symptoms_same_day: list[str] = Field(default_factory=list)
    symptoms_next_day: list[str] = Field(default_factory=list)
    puffs_today: int = 0
    triggers: list[str] = Field(default_factory=list)
    matched_on: list[str] = Field(default_factory=list)
    relevance_score: float = 0.0


class HistoryContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    window_days: int
    episodes: list[HistoricalEpisode] = Field(default_factory=list)
    metric_windows: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)


class PersonalInsight(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["pattern", "trend", "statistic"]
    label: str
    statement: str
    evidence_strength: Literal["insufficient", "low", "moderate", "high"]
    statistics: dict[str, int | float | str | None] = Field(default_factory=dict)
    supporting_dates: list[date] = Field(default_factory=list)


class InsightsContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    patterns: list[PersonalInsight] = Field(default_factory=list)
    trends: list[PersonalInsight] = Field(default_factory=list)
    statistics: list[PersonalInsight] = Field(default_factory=list)


class KnowledgeChunk(BaseModel):
    model_config = ConfigDict(extra="allow")

    chunk_id: str
    title: str
    body: str
    publisher: str = "local"
    source_url: str | None = None
    section: str | None = None
    tags: list[str] = Field(default_factory=list)
    audience: KnowledgeAudience = "patient"
    medication_change_allowed: bool = False
    advice_types: list[AdviceType] = Field(default_factory=lambda: ["daily"])


class AdviceSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    body: str = Field(min_length=1)


class EvidenceRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunk_id: str
    title: str
    publisher: str
    source_url: str | None = None
    audience: KnowledgeAudience
    medication_change_allowed: bool = False


class AdviceResponse(BaseModel):
    """Backward-compatible advice payload plus optional grounding metadata."""

    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1)
    # Chat replies may use summary-only; daily advice still prompts for sections.
    sections: list[AdviceSection] = Field(default_factory=list, max_length=5)
    disclaimer: str = Field(min_length=1)
    llm_provider: str
    knowledge_sources_used: list[str] = Field(default_factory=list)
    evidence: list[EvidenceRef] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class CopilotState(TypedDict):
    forecast: dict[str, Any]
    calendar: list[dict[str, Any]]
    environment: dict[str, Any]
    profile: dict[str, Any]
    history: dict[str, Any]
    insights: dict[str, Any]
    knowledge: list[dict[str, Any]]
    question: str | None
    advice_type: AdviceType
    audience: KnowledgeAudience
    prompt: str
    llm_response: dict[str, Any]
    validated_response: dict[str, Any]
    warnings: list[str]
    llm_provider: NotRequired[str]
    _history_analysis_pool: NotRequired[list[dict[str, Any]]]
