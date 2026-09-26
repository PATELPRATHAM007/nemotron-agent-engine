"""
Persistent Database Models for Identity, Security & Authorization
================================================================
Implements:
  - Users, Organizations, Projects, Repositories, Roles, Permissions
  - User Sessions & Rotating Refresh Tokens
  - Local Agent Identities & Sessions
  - Immutable Security Audit Events & Security Violations
"""

from datetime import datetime, timezone
from typing import Any
import uuid

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    """User identity record."""

    __tablename__ = "security_users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(256), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(256), default="")
    hashed_password: Mapped[str] = mapped_column(String(512), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True, default="default-tenant")

    # Roles assigned to user (list of role names, e.g. ["DEVELOPER", "PROJECT_ADMIN"])
    roles: Mapped[list[str]] = mapped_column(JSON, default=lambda: ["DEVELOPER"])

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    sessions: Mapped[list["UserSession"]] = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "tenant_id": self.tenant_id,
            "roles": self.roles,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Organization(Base):
    """Tenant / Organization grouping for multi-tenant isolation."""

    __tablename__ = "security_organizations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    tier: Mapped[str] = mapped_column(String(64), default="standard")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "tier": self.tier,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Project(Base):
    """Project unit containing repositories and autonomous missions."""

    __tablename__ = "security_projects"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(String(64), ForeignKey("security_organizations.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "name": self.name,
            "slug": self.slug,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class UserSession(Base):
    """Server-side authenticated session for browser or client."""

    __tablename__ = "security_user_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("security_users.id", ondelete="CASCADE"), index=True, nullable=False)
    session_token_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    device_info: Mapped[str] = mapped_column(String(256), default="browser")
    ip_address: Mapped[str] = mapped_column(String(64), default="127.0.0.1")
    user_agent: Mapped[str] = mapped_column(String(512), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    last_active_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    user: Mapped["User"] = relationship("User", back_populates="sessions")
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship("RefreshToken", back_populates="session", cascade="all, delete-orphan")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "device_info": self.device_info,
            "ip_address": self.ip_address,
            "is_active": self.is_active,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_active_at": self.last_active_at.isoformat() if self.last_active_at else None,
        }


class RefreshToken(Base):
    """Rotating refresh token with family tracking for reuse detection."""

    __tablename__ = "security_refresh_tokens"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String(64), ForeignKey("security_user_sessions.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    family_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    session: Mapped["UserSession"] = relationship("UserSession", back_populates="refresh_tokens")


class Agent(Base):
    """Local execution agent identity with registered public key."""

    __tablename__ = "security_agents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    project_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    device_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE")  # ACTIVE, OFFLINE, REVOKED
    public_key: Mapped[str] = mapped_column(Text, nullable=False)
    capabilities: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "project_id": self.project_id,
            "device_id": self.device_id,
            "status": self.status,
            "capabilities": self.capabilities,
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AuditEvent(Base):
    """Immutable audit trail for identity, permission, and tool actions."""

    __tablename__ = "security_audit_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    actor_type: Mapped[str] = mapped_column(String(32), nullable=False)  # user, agent, service, system
    actor_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    organization_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    project_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    mission_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)

    action: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    result: Mapped[str] = mapped_column(String(32), default="SUCCESS")  # SUCCESS, DENIED, FAILED
    reason: Mapped[str] = mapped_column(Text, default="")
    source_ip: Mapped[str] = mapped_column(String(64), default="127.0.0.1")
    user_agent: Mapped[str] = mapped_column(String(512), default="")
    event_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "actor_type": self.actor_type,
            "actor_id": self.actor_id,
            "organization_id": self.organization_id,
            "project_id": self.project_id,
            "mission_id": self.mission_id,
            "request_id": self.request_id,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "result": self.result,
            "reason": self.reason,
            "source_ip": self.source_ip,
            "metadata": self.event_metadata,
        }


class SecurityEvent(Base):
    """Security alert event (SSRF attempt, prompt injection, quota breach, etc.)."""

    __tablename__ = "security_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    severity: Mapped[str] = mapped_column(String(32), default="INFO")  # INFO, WARNING, HIGH, CRITICAL
    actor_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    source_ip: Mapped[str] = mapped_column(String(64), default="127.0.0.1")
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "event_type": self.event_type,
            "severity": self.severity,
            "actor_id": self.actor_id,
            "source_ip": self.source_ip,
            "details": self.details,
        }
