"""
Autonomous Mission Intelligence Subsystem
=========================================
Persistent models, state machine, permission engine, multimodal context,
slash commands, and mission repository.
"""

from app.intelligence.missions.models import (
    Mission,
    MissionArtifact,
    MissionAttachment,
    MissionCheckpoint,
    MissionDiff,
    MissionEvent,
    MissionMessage,
    MissionPermissionRequest,
    MissionPlan,
    MissionSelection,
)
from app.intelligence.missions.multimodal import multimodal_storage
from app.intelligence.missions.permissions import (
    CommandRiskClassifier,
    MissionPermissionEngine,
    PermissionDecision,
    PermissionScope,
    RiskLevel,
    mission_permissions,
)
from app.intelligence.missions.repository import mission_repository
from app.intelligence.missions.slash_commands import SlashCommandParser
from app.intelligence.missions.state_machine import MissionState, MissionStateMachine

__all__ = [
    "Mission",
    "MissionMessage",
    "MissionAttachment",
    "MissionEvent",
    "MissionPlan",
    "MissionSelection",
    "MissionPermissionRequest",
    "MissionDiff",
    "MissionCheckpoint",
    "MissionArtifact",
    "MissionState",
    "MissionStateMachine",
    "RiskLevel",
    "PermissionDecision",
    "PermissionScope",
    "CommandRiskClassifier",
    "MissionPermissionEngine",
    "mission_permissions",
    "multimodal_storage",
    "SlashCommandParser",
    "mission_repository",
]
