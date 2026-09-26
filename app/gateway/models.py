"""
Persistent Database Models for Model Gateway & Registry
=======================================================
Stores:
  - Model Providers (Google, OpenAI, Anthropic, vLLM, Ollama)
  - Registered Models & Capabilities (Text, Vision, Tools, Code, Reasoning)
  - Model Credentials (References only, NEVER plaintext)
  - Model Usage & Billing Audits
  - Model Quotas & Rate Limits
"""

from datetime import datetime, timezone
from typing import Any
import uuid

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ModelProvider(Base):
    """External or self-hosted model service provider."""

    __tablename__ = "gateway_model_providers"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    provider_type: Mapped[str] = mapped_column(String(64), nullable=False)  # GOOGLE, OPENAI, ANTHROPIC, VLLM, OLLAMA, CUSTOM
    base_url: Mapped[str] = mapped_column(String(512), default="")
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE")  # ACTIVE, DEGRADED, OFFLINE
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    models: Mapped[list["RegisteredModel"]] = relationship("RegisteredModel", back_populates="provider", cascade="all, delete-orphan")
    credentials: Mapped[list["ModelCredential"]] = relationship("ModelCredential", back_populates="provider", cascade="all, delete-orphan")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "provider_type": self.provider_type,
            "base_url": self.base_url,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class RegisteredModel(Base):
    """Registered AI model available through the Model Gateway."""

    __tablename__ = "gateway_registered_models"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    provider_id: Mapped[str] = mapped_column(String(64), ForeignKey("gateway_model_providers.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    model_identifier: Mapped[str] = mapped_column(String(256), nullable=False)  # e.g. gemini-3.1-flash-lite, claude-3-5-sonnet

    # Capabilities: ["text", "vision", "tools", "code", "reasoning"]
    capabilities: Mapped[list[str]] = mapped_column(JSON, default=lambda: ["text", "code", "tools"])
    context_window: Mapped[int] = mapped_column(Integer, default=128000)
    max_output_tokens: Mapped[int] = mapped_column(Integer, default=8192)

    # Cost accounting per 1,000 tokens
    cost_per_1k_input: Mapped[float] = mapped_column(Float, default=0.0001)
    cost_per_1k_output: Mapped[float] = mapped_column(Float, default=0.0003)

    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    provider: Mapped["ModelProvider"] = relationship("ModelProvider", back_populates="models")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "provider_id": self.provider_id,
            "name": self.name,
            "model_identifier": self.model_identifier,
            "capabilities": self.capabilities,
            "context_window": self.context_window,
            "max_output_tokens": self.max_output_tokens,
            "cost_per_1k_input": self.cost_per_1k_input,
            "cost_per_1k_output": self.cost_per_1k_output,
            "is_premium": self.is_premium,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ModelCredential(Base):
    """Metadata reference to provider secrets stored in SecretManager / Vault."""

    __tablename__ = "gateway_model_credentials"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    provider_id: Mapped[str] = mapped_column(String(64), ForeignKey("gateway_model_providers.id", ondelete="CASCADE"), index=True, nullable=False)
    secret_reference: Mapped[str] = mapped_column(String(512), nullable=False)  # vault://models/...
    key_version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE")  # ACTIVE, ROTATING, REVOKED
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    last_rotated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    provider: Mapped["ModelProvider"] = relationship("ModelProvider", back_populates="credentials")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "provider_id": self.provider_id,
            "secret_reference": self.secret_reference,
            "key_version": self.key_version,
            "status": self.status,
            "last_rotated_at": self.last_rotated_at.isoformat() if self.last_rotated_at else None,
        }


class ModelUsage(Base):
    """Audit record for individual model calls."""

    __tablename__ = "gateway_model_usage"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    mission_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    organization_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    project_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    model_name: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    provider_type: Mapped[str] = mapped_column(String(64), nullable=False)

    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(32), default="SUCCESS")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "mission_id": self.mission_id,
            "user_id": self.user_id,
            "organization_id": self.organization_id,
            "model_name": self.model_name,
            "total_tokens": self.total_tokens,
            "cost_usd": self.cost_usd,
            "latency_ms": self.latency_ms,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ModelQuota(Base):
    """Spending limits and rate limits per tenant / user."""

    __tablename__ = "gateway_model_quotas"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    max_monthly_spend_usd: Mapped[float] = mapped_column(Float, default=500.0)
    max_daily_spend_usd: Mapped[float] = mapped_column(Float, default=50.0)
    max_requests_per_minute: Mapped[int] = mapped_column(Integer, default=120)
    current_month_spend_usd: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "max_monthly_spend_usd": self.max_monthly_spend_usd,
            "max_daily_spend_usd": self.max_daily_spend_usd,
            "max_requests_per_minute": self.max_requests_per_minute,
            "current_month_spend_usd": self.current_month_spend_usd,
        }
