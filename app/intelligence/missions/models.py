"""
Persistent Database Models for Autonomous Missions
==================================================
Stores missions, messages, events, plans, selections, permissions,
checkpoints, diffs, artifacts, and multimodal attachments.
"""

from datetime import datetime, timezone
from typing import Any
import uuid

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Mission(Base):
    """Primary unit of persistent autonomous software engineering work."""

    __tablename__ = "missions"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False, default="Autonomous Mission")
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="IDLE", index=True)
    current_phase: Mapped[str] = mapped_column(String(64), default="INIT")
    execution_policy: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    
    # Telemetry
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    # Relationships
    messages: Mapped[list["MissionMessage"]] = relationship("MissionMessage", back_populates="mission", cascade="all, delete-orphan")
    events: Mapped[list["MissionEvent"]] = relationship("MissionEvent", back_populates="mission", cascade="all, delete-orphan")
    plans: Mapped[list["MissionPlan"]] = relationship("MissionPlan", back_populates="mission", cascade="all, delete-orphan")
    checkpoints: Mapped[list["MissionCheckpoint"]] = relationship("MissionCheckpoint", back_populates="mission", cascade="all, delete-orphan")
    artifacts: Mapped[list["MissionArtifact"]] = relationship("MissionArtifact", back_populates="mission", cascade="all, delete-orphan")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "goal": self.goal,
            "status": self.status,
            "current_phase": self.current_phase,
            "execution_policy": self.execution_policy,
            "total_tokens": self.total_tokens,
            "total_cost_usd": self.total_cost_usd,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class MissionMessage(Base):
    """Persistent chat message in the Autonomous Mission timeline."""

    __tablename__ = "mission_messages"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    mission_id: Mapped[str] = mapped_column(String(64), ForeignKey("missions.id", ondelete="CASCADE"), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # user, assistant, system
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    mission: Mapped["Mission"] = relationship("Mission", back_populates="messages")
    attachments: Mapped[list["MissionAttachment"]] = relationship("MissionAttachment", back_populates="message", cascade="all, delete-orphan")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "mission_id": self.mission_id,
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "attachments": [a.to_dict() for a in self.attachments] if self.attachments else [],
        }


class MissionAttachment(Base):
    """Multimodal binary attachment (screenshot, image, diagram) metadata."""

    __tablename__ = "mission_attachments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    mission_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    message_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("mission_messages.id", ondelete="CASCADE"), nullable=True)
    filename: Mapped[str] = mapped_column(String(256), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(64), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_reference: Mapped[str] = mapped_column(String(512), nullable=False)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    message: Mapped["MissionMessage"] = relationship("MissionMessage", back_populates="attachments")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "mission_id": self.mission_id,
            "message_id": self.message_id,
            "filename": self.filename,
            "mime_type": self.mime_type,
            "file_size": self.file_size,
            "storage_reference": self.storage_reference,
            "sha256_hash": self.sha256_hash,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class MissionEvent(Base):
    """Append-only audit event in the Mission Execution stream."""

    __tablename__ = "mission_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    mission_id: Mapped[str] = mapped_column(String(64), ForeignKey("missions.id", ondelete="CASCADE"), index=True, nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    causation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    mission: Mapped["Mission"] = relationship("Mission", back_populates="events")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "mission_id": self.mission_id,
            "sequence": self.sequence,
            "event_type": self.event_type,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


class MissionPlan(Base):
    """Structured plan with executable steps and approval status."""

    __tablename__ = "mission_plans"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    mission_id: Mapped[str] = mapped_column(String(64), ForeignKey("missions.id", ondelete="CASCADE"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="PROPOSED")  # PROPOSED, APPROVED, MODIFIED, REJECTED
    steps: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    summary: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    mission: Mapped["Mission"] = relationship("Mission", back_populates="plans")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "mission_id": self.mission_id,
            "status": self.status,
            "steps": self.steps,
            "summary": self.summary,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class MissionSelection(Base):
    """Multiple-solution choices or structured questions during execution."""

    __tablename__ = "mission_selections"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    mission_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    recommended_option: Mapped[str | None] = mapped_column(String(64), nullable=True)
    selected_option: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="PENDING")  # PENDING, ANSWERED, EXPIRED
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "mission_id": self.mission_id,
            "prompt": self.prompt,
            "options": self.options,
            "recommended_option": self.recommended_option,
            "selected_option": self.selected_option,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "answered_at": self.answered_at.isoformat() if self.answered_at else None,
        }


class MissionPermissionRequest(Base):
    """Fine-grained interactive permission approval request."""

    __tablename__ = "mission_permission_requests"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    mission_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)  # command, write_file, git_push, etc.
    target: Mapped[str] = mapped_column(String(512), nullable=False)
    directory: Mapped[str] = mapped_column(String(512), default=".")
    risk_level: Mapped[str] = mapped_column(String(32), default="LOW")  # SAFE, LOW, MEDIUM, HIGH, CRITICAL
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="PENDING")  # PENDING, GRANTED, DENIED, EXPIRED
    granted_scope: Mapped[str | None] = mapped_column(String(32), nullable=True)  # ONCE, MISSION, PROJECT, ALWAYS
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "mission_id": self.mission_id,
            "action": self.action,
            "target": self.target,
            "directory": self.directory,
            "risk_level": self.risk_level,
            "reason": self.reason,
            "status": self.status,
            "granted_scope": self.granted_scope,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "decided_at": self.decided_at.isoformat() if self.decided_at else None,
        }


class MissionDiff(Base):
    """Interactive unified diff generated during file modification workflow."""

    __tablename__ = "mission_diffs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    mission_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    diff_content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="PENDING")  # PENDING, ACCEPTED, REJECTED, MODIFIED
    comments: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "mission_id": self.mission_id,
            "file_path": self.file_path,
            "diff_content": self.diff_content,
            "status": self.status,
            "comments": self.comments,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class MissionCheckpoint(Base):
    """Persistent snapshot for crash recovery and session resumption."""

    __tablename__ = "mission_checkpoints"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    mission_id: Mapped[str] = mapped_column(String(64), ForeignKey("missions.id", ondelete="CASCADE"), index=True, nullable=False)
    phase: Mapped[str] = mapped_column(String(64), nullable=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    mission: Mapped["Mission"] = relationship("Mission", back_populates="checkpoints")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "mission_id": self.mission_id,
            "phase": self.phase,
            "snapshot": self.snapshot,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class MissionArtifact(Base):
    """Structured artifact generated by the autonomous agent."""

    __tablename__ = "mission_artifacts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    mission_id: Mapped[str] = mapped_column(String(64), ForeignKey("missions.id", ondelete="CASCADE"), index=True, nullable=False)
    artifact_type: Mapped[str] = mapped_column(String(64), nullable=False)  # plan, diff, test_report, architecture, summary
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    mission: Mapped["Mission"] = relationship("Mission", back_populates="artifacts")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "mission_id": self.mission_id,
            "artifact_type": self.artifact_type,
            "title": self.title,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
