"""
Database Model Central Registry
===============================
Imports Base and all persistent SQLAlchemy models across domain modules
so that Alembic migrations and database initialization see the full schema.
"""

from app.db.session import Base
from app.modules.auth.models import (  # noqa: F401
    Agent,
    AuditEvent,
    Organization,
    Project,
    RefreshToken,
    SecurityEvent,
    User,
    UserSession,
)
from app.modules.cost.models import CostRecord  # noqa: F401
from app.modules.gateway.models import (  # noqa: F401
    ModelCredential,
    ModelProvider,
    ModelQuota,
    ModelUsage,
    RegisteredModel,
)
from app.modules.missions.models import (  # noqa: F401
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
    "Base",
    "CostRecord",
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
    "User",
    "Organization",
    "Project",
    "UserSession",
    "RefreshToken",
    "Agent",
    "AuditEvent",
    "SecurityEvent",
    "ModelProvider",
    "RegisteredModel",
    "ModelCredential",
    "ModelUsage",
    "ModelQuota",
]
