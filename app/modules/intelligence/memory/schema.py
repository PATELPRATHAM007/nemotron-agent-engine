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


class MemoryTier(str, Enum):
    SESSION = "SESSION"  # Ephemeral active mission state
    PROJECT = "PROJECT"  # Durable repository memory (.agent/memory/project_memory.json)
    USER = "USER"  # Cross-project developer preferences


class CompactionSnapshot(BaseModel):
    mission_id: str
    goal: str
    completed_steps: list[str] = Field(default_factory=list)
    pending_steps: list[str] = Field(default_factory=list)
    files_modified: list[str] = Field(default_factory=list)
    key_decisions: list[str] = Field(default_factory=list)
    active_errors: list[str] = Field(default_factory=list)
    next_immediate_action: str = ""
    timestamp: float = Field(default_factory=time.time)
    token_count_before: int = 0
    token_count_after: int = 0


class SessionMemory(BaseModel):
    mission_id: str
    active_files: list[str] = Field(default_factory=list)
    hypotheses: list[str] = Field(default_factory=list)
    active_errors: list[str] = Field(default_factory=list)
    scratchpad: str = ""
    plan_steps: list[dict] = Field(default_factory=list)
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)


class ProjectMemoryItem(BaseModel):
    item_id: str
    category: str = "convention"  # convention, architecture, database, gotcha, standard
    title: str
    content: str
    confidence_score: float = 0.8
    tags: list[str] = Field(default_factory=list)
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)


class UserPreference(BaseModel):
    key: str
    value: str
    category: str = "general"  # style, tooling, commit, test
    source: str = "developer"
    last_updated: float = Field(default_factory=time.time)


class MemoryCandidate(BaseModel):
    title: str
    content: str
    category: str = "general"
    tier: MemoryTier = MemoryTier.PROJECT
    scope: str = "project"  # project or user
    confidence: float = 0.8

