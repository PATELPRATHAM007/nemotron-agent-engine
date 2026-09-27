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


def __getattr__(name: str):
    if name == "router":
        from app.modules.missions.router import router
        return router
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "Mission",
    "MissionMessage",
    "MissionPlan",
    "MissionCheckpoint",
    "MissionArtifact",
    "MissionStateMachine",
    "MissionState",
    "MissionPermissionEngine",
    "CommandRiskClassifier",
    "RiskLevel",
    "PermissionScope",
    "PermissionDecision",
    "mission_permissions",
    "MultimodalStorage",
    "multimodal_storage",
    "SlashCommandParser",
    "MissionRepository",
    "mission_repository",
    "router",
]
