"""
Cost Record Database Repository
================================
CRUD operations for persisting and querying cost records
from the SQL database via SQLAlchemy.
"""

from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.modules.cost.models import CostRecord
from app.modules.cost.schemas import (
    LedgerSummary,
    MissionCostReport,
)

logger = get_logger(__name__)


class CostRepository:
    """Database repository for cost record persistence and aggregation queries."""

    def __init__(self, session: Session):
        self.session = session

    def save_record(self, report: MissionCostReport, model_engine: str = "nemotron-3-ultra") -> CostRecord:
        """Persist a MissionCostReport to the database."""
        record = CostRecord(
            mission_id=report.mission_id,
            target_feature=report.target_feature,
            model_engine=model_engine,
            pricing_mode=report.pricing_mode.value,
            prompt_tokens=report.usage.prompt_tokens,
            completion_tokens=report.usage.completion_tokens,
            thinking_tokens=report.usage.thinking_tokens,
            total_tokens=report.usage.total_tokens,
            duration_seconds=report.duration_seconds,
            total_cost_usd=report.total_cost_usd,
            estimated_savings_usd=report.estimated_savings_usd,
            effective_rate_per_1k=report.effective_rate_per_1k_tokens_usd,
            alert_level=report.alert_level.value,
            created_at=datetime.fromtimestamp(report.timestamp, tz=timezone.utc),
        )
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        logger.info(
            f"DB: Recorded mission {record.mission_id}: "
            f"{record.total_tokens} tokens, ${record.total_cost_usd:.4f} USD"
        )
        return record

    def get_recent_records(self, limit: int = 10) -> list[dict]:
        """Return the most recent cost records ordered by created_at descending."""
        records = (
            self.session.query(CostRecord)
            .order_by(CostRecord.created_at.desc())
            .limit(limit)
            .all()
        )
        return [self._record_to_dict(r) for r in records]

    def get_daily_spend(self, target_date: str | None = None) -> float:
        """Calculate cumulative spend for a given UTC day (format: YYYY-MM-DD)."""
        if target_date:
            date_obj = datetime.strptime(target_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        else:
            date_obj = datetime.now(timezone.utc)

        start_of_day = date_obj.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = date_obj.replace(hour=23, minute=59, second=59, microsecond=999999)

        result = (
            self.session.query(func.coalesce(func.sum(CostRecord.total_cost_usd), 0.0))
            .filter(CostRecord.created_at >= start_of_day)
            .filter(CostRecord.created_at <= end_of_day)
            .scalar()
        )
        return round(float(result), 4)

    def get_summary(self) -> LedgerSummary:
        """Compute aggregated audit metrics across all recorded missions in DB."""
        total_missions = self.session.query(func.count(CostRecord.id)).scalar() or 0
        total_tokens = (
            self.session.query(func.coalesce(func.sum(CostRecord.total_tokens), 0)).scalar()
        )
        total_spend = (
            self.session.query(func.coalesce(func.sum(CostRecord.total_cost_usd), 0.0)).scalar()
        )
        total_saved = (
            self.session.query(
                func.coalesce(func.sum(CostRecord.estimated_savings_usd), 0.0)
            ).scalar()
        )
        daily_spend = self.get_daily_spend()

        # Spend by model engine
        engine_rows = (
            self.session.query(
                CostRecord.model_engine,
                func.sum(CostRecord.total_cost_usd),
            )
            .group_by(CostRecord.model_engine)
            .all()
        )
        spend_by_role = {row[0]: round(float(row[1]), 4) for row in engine_rows}

        return LedgerSummary(
            total_missions=int(total_missions),
            total_tokens=int(total_tokens),
            total_spend_usd=round(float(total_spend), 4),
            total_saved_usd=round(float(total_saved), 4),
            daily_spend_usd=round(float(daily_spend), 4),
            spend_by_role=spend_by_role,
        )

    def get_records_by_mission(self, mission_id: str) -> list[dict]:
        """Retrieve all cost records for a specific mission."""
        records = (
            self.session.query(CostRecord)
            .filter(CostRecord.mission_id == mission_id)
            .order_by(CostRecord.created_at.desc())
            .all()
        )
        return [self._record_to_dict(r) for r in records]

    @staticmethod
    def _record_to_dict(record: CostRecord) -> dict:
        """Convert a CostRecord ORM instance to a serializable dictionary."""
        return {
            "id": record.id,
            "mission_id": record.mission_id,
            "target_feature": record.target_feature,
            "model_engine": record.model_engine,
            "pricing_mode": record.pricing_mode,
            "prompt_tokens": record.prompt_tokens,
            "completion_tokens": record.completion_tokens,
            "thinking_tokens": record.thinking_tokens,
            "total_tokens": record.total_tokens,
            "tokens_used": record.total_tokens,
            "usage": {
                "prompt_tokens": record.prompt_tokens,
                "completion_tokens": record.completion_tokens,
                "thinking_tokens": record.thinking_tokens,
                "total_tokens": record.total_tokens,
            },
            "duration_seconds": record.duration_seconds,
            "total_cost_usd": record.total_cost_usd,
            "cost_usd": record.total_cost_usd,
            "estimated_savings_usd": record.estimated_savings_usd,
            "effective_rate_per_1k": record.effective_rate_per_1k,
            "alert_level": record.alert_level,
            "created_at": record.created_at.isoformat() if record.created_at else None,
        }
