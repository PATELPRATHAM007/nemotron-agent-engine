"""
Memory and Architecture Decision Record (ADR) Schemas
====================================================
Defines schemas for institutional memory, historical lessons learned,
and repository architectural decisions.
"""

import time
from enum import Enum

from pydantic import BaseModel, Field


class ADRStatus(str, Enum):
    PROPOSED = "PROPOSED"
    ACCEPTED = "ACCEPTED"
    SUPERSEDED = "SUPERSEDED"
    DEPRECATED = "DEPRECATED"


class ADRRecord(BaseModel):
    adr_id: str  # e.g., "ADR-001"
    title: str
    status: ADRStatus = ADRStatus.ACCEPTED
    date: str
    context: str
    decision: str
    consequences: str
    affected_modules: list[str] = Field(default_factory=list)


class LessonCategory(str, Enum):
    BUG_FIX = "BUG_FIX"
    ANTI_PATTERN = "ANTI_PATTERN"
    PERFORMANCE = "PERFORMANCE"
    SECURITY = "SECURITY"
    ARCHITECTURAL = "ARCHITECTURAL"


class HistoricalLesson(BaseModel):
    lesson_id: str
    category: LessonCategory
    title: str
    description: str
    trigger_pattern: str  # keyword or regex pattern indicating when this lesson applies
    resolution: str
    confidence_score: float = 0.8  # 0.0 to 1.0
    occurrences: int = 1
    last_updated: float = Field(default_factory=time.time)
