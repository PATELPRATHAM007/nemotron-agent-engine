"""
Server-Side Authorization & Model Access Context
================================================
Constructs immutable, authoritative security context from validated tokens,
server-side sessions, and tenant ownership records.
NEVER trusts arbitrary claims or IDs sent in request body from the client.
"""

from dataclasses import dataclass, field
from typing import Any
import uuid


@dataclass(frozen=True)
class AuthContext:
    """Immutable server-side authentication and authorization context."""

    user_id: str
    organization_id: str
    project_id: str | None = None
    session_id: str | None = None
    roles: tuple[str, ...] = ("DEVELOPER",)
    scopes: tuple[str, ...] = ("model.use", "repository.read")
    permissions: tuple[str, ...] = ()
    authentication_method: str = "bearer_token"  # bearer_token, session_cookie, agent_key
    is_agent: bool = False
    agent_id: str | None = None
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_ip: str = "127.0.0.1"

    def has_role(self, role: str) -> bool:
        return role in self.roles or "SUPER_ADMIN" in self.roles

    def has_permission(self, permission: str) -> bool:
        if "SUPER_ADMIN" in self.roles or "admin" in self.roles:
            return True
        return permission in self.permissions or permission in self.scopes

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "organization_id": self.organization_id,
            "project_id": self.project_id,
            "session_id": self.session_id,
            "roles": list(self.roles),
            "scopes": list(self.scopes),
            "permissions": list(self.permissions),
            "authentication_method": self.authentication_method,
            "is_agent": self.is_agent,
            "agent_id": self.agent_id,
            "request_id": self.request_id,
            "source_ip": self.source_ip,
        }


@dataclass(frozen=True)
class ModelAccessContext:
    """Enriched security context required for every model call through the Model Gateway."""

    user_id: str
    organization_id: str
    project_id: str
    model_id: str
    mission_id: str | None = None
    repository_id: str | None = None
    conversation_id: str | None = None
    agent_run_id: str | None = None
    scopes: tuple[str, ...] = ("model.use",)
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "organization_id": self.organization_id,
            "project_id": self.project_id,
            "model_id": self.model_id,
            "mission_id": self.mission_id,
            "repository_id": self.repository_id,
            "conversation_id": self.conversation_id,
            "agent_run_id": self.agent_run_id,
            "scopes": list(self.scopes),
            "request_id": self.request_id,
            "session_id": self.session_id,
        }
