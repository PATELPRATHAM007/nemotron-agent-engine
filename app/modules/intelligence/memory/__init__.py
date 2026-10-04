"""
Institutional Memory & ADR Module
=================================
Manages ADRs, historical lessons, and adaptive confidence scoring.
"""

from app.modules.intelligence.memory.adr_manager import ADRManager
from app.modules.intelligence.memory.memory_store import InstitutionalMemoryStore
from app.modules.intelligence.memory.schema import (
    ADRRecord,
    ADRStatus,
    CompactionSnapshot,
    HistoricalLesson,
    LessonCategory,
    MemoryCandidate,
    MemoryTier,
    ProjectMemoryItem,
    SessionMemory,
    UserPreference,
)
from app.modules.intelligence.memory.three_tier_store import (
    MemoryDurabilityGate,
    ThreeTierMemoryStore,
)

__all__ = [
    "ADRManager",
    "ADRRecord",
    "ADRStatus",
    "CompactionSnapshot",
    "HistoricalLesson",
    "InstitutionalMemoryStore",
    "LessonCategory",
    "MemoryCandidate",
    "MemoryDurabilityGate",
    "MemoryTier",
    "ProjectMemoryItem",
    "SessionMemory",
    "ThreeTierMemoryStore",
    "UserPreference",
]

