"""
Database Model Central Registry
===============================
Imports Base and all persistent SQLAlchemy models across domain modules
so that Alembic migrations and database initialization see the full schema.
"""

from app.db.session import Base
from app.modules.auth.models import (
    Agent,
    AuditEvent,
    Organization,
    Project,
    RefreshToken,
    SecurityEvent,
    User,
    UserSession,
)
from app.modules.cost.models import CostRecord
from app.modules.gateway.models import (
    ModelCredential,
    ModelProvider,
    ModelQuota,
    ModelUsage,
    RegisteredModel,
)
from app.modules.missions.models import (
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

__all__ = [
    "Agent",
    "AuditEvent",
    "Base",
    "CostRecord",
    "Mission",
    "MissionArtifact",
    "MissionAttachment",
    "MissionCheckpoint",
    "MissionDiff",
    "MissionEvent",
    "MissionMessage",
    "MissionPermissionRequest",
    "MissionPlan",
    "MissionSelection",
    "ModelCredential",
    "ModelProvider",
    "ModelQuota",
    "ModelUsage",
    "Organization",
    "Project",
    "RefreshToken",
    "RegisteredModel",
    "SecurityEvent",
    "User",
    "UserSession",
]
