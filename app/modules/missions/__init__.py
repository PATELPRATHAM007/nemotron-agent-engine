"""
Autonomous Missions Module
==========================
Unified Autonomous Mission Chat, interactive state machine, permissions, and multimodal execution.
"""
from app.modules.missions.models import (
    Mission,
    MissionArtifact,
    MissionCheckpoint,
    MissionMessage,
    MissionPlan,
)
from app.modules.missions.multimodal import MultimodalStorage, multimodal_storage
from app.modules.missions.permissions import (
    CommandRiskClassifier,
    MissionPermissionEngine,
    PermissionDecision,
    PermissionScope,
    RiskLevel,
    mission_permissions,
)
from app.modules.missions.repository import MissionRepository, mission_repository
from app.modules.missions.slash_commands import SlashCommandParser
from app.modules.missions.state_machine import MissionState, MissionStateMachine


__all__ = [
    "CommandRiskClassifier",
    "Mission",
    "MissionArtifact",
    "MissionCheckpoint",
    "MissionMessage",
    "MissionPermissionEngine",
    "MissionPlan",
    "MissionRepository",
    "MissionState",
    "MissionStateMachine",
    "MultimodalStorage",
    "PermissionDecision",
    "PermissionScope",
    "RiskLevel",
    "SlashCommandParser",
    "mission_permissions",
    "mission_repository",
    "multimodal_storage",
]
