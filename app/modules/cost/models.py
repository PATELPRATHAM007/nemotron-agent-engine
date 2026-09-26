"""
Cost Record SQLAlchemy ORM Model
================================
Persistent database table for token usage, financial spend,
and mission cost audit records.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class CostRecord(Base):
    """Stores per-mission token usage and financial expenditure records."""

    __tablename__ = "cost_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mission_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    target_feature: Mapped[str] = mapped_column(String(128), default="general")
    model_engine: Mapped[str] = mapped_column(String(64), default="nemotron-3-ultra")
    pricing_mode: Mapped[str] = mapped_column(String(32), default="gcp_spot")

    # Token Breakdown
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    thinking_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)

    # Financial Metrics
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    total_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    estimated_savings_usd: Mapped[float] = mapped_column(Float, default=0.0)
    effective_rate_per_1k: Mapped[float] = mapped_column(Float, default=0.0)

    # Budget Alert
    alert_level: Mapped[str] = mapped_column(String(32), default="NORMAL")

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    def __repr__(self) -> str:
        return (
            f"<CostRecord(id={self.id}, mission={self.mission_id}, "
            f"tokens={self.total_tokens}, cost=${self.total_cost_usd:.4f})>"
        )
