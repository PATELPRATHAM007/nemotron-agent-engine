"""
Persistent Cost Ledger & Financial Audit Store
==============================================
Records mission telemetry and spend audit trails to `.agent/memory/cost_ledger.json`.
Provides rollups for daily budgets, historical analytics, and savings reports.
"""

import json
import os
import time
from datetime import datetime, timezone

from app.core.logging_config import get_logger
from app.intelligence.cost.schema import (
    LedgerSummary,
    MissionCostReport,
)

logger = get_logger(__name__)


class CostLedger:
    """Manages append-only persistent audit records for agent token and dollar expenditures."""

    def __init__(self, workspace_root: str):
        self.workspace_root = os.path.abspath(workspace_root)
        self.ledger_dir = os.path.join(self.workspace_root, ".agent", "memory")
        self.ledger_file = os.path.join(self.ledger_dir, "cost_ledger.json")
        self._records: list[MissionCostReport] = []
        self._load()

    def _ensure_dir(self) -> None:
        os.makedirs(self.ledger_dir, exist_ok=True)

    def _load(self) -> None:
        if os.path.exists(self.ledger_file):
            try:
                with open(self.ledger_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._records = [MissionCostReport(**item) for item in data]
            except (OSError, json.JSONDecodeError, KeyError, ValueError) as e:
                logger.error(f"Failed to load cost ledger from {self.ledger_file}: {e}")
                self._records = []

    def _save(self) -> None:
        self._ensure_dir()
        temp_file = f"{self.ledger_file}.tmp"
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump([r.model_dump() for r in self._records], f, indent=2)
            os.replace(temp_file, self.ledger_file)
        except (OSError, TypeError, ValueError) as e:
            logger.error(f"Failed to save cost ledger: {e}")

    def record_mission(self, report: MissionCostReport) -> None:
        """Record a completed mission's financial and token report."""
        self._records.append(report)
        self._save()
        logger.info(
            f"Ledger recorded mission {report.mission_id}: "
            f"{report.usage.total_tokens} tokens, ${report.total_cost_usd:.4f} USD"
        )

    def get_daily_spend(self, target_date: str | None = None) -> float:
        """Calculate cumulative spend for a given day (format: YYYY-MM-DD)."""
        date_prefix = target_date or datetime.fromtimestamp(
            time.time(), tz=timezone.utc
        ).strftime("%Y-%m-%d")
        total = 0.0

        for r in self._records:
            record_date = datetime.fromtimestamp(r.timestamp, tz=timezone.utc).strftime(
                "%Y-%m-%d"
            )
            if record_date == date_prefix:
                total += r.total_cost_usd

        return round(total, 4)

    def get_recent_missions(self, limit: int = 10) -> list[MissionCostReport]:
        """Return the most recent mission reports ordered by timestamp descending."""
        return sorted(self._records, key=lambda x: x.timestamp, reverse=True)[:limit]

    def get_summary(self) -> LedgerSummary:
        """Compute aggregated audit metrics across all recorded missions."""
        total_tokens = sum(r.usage.total_tokens for r in self._records)
        total_spend = sum(r.total_cost_usd for r in self._records)
        total_saved = sum(r.estimated_savings_usd for r in self._records)
        daily_spend = self.get_daily_spend()

        role_spend: dict[str, float] = {}
        for r in self._records:
            total_mission_tokens = max(1, r.usage.total_tokens)
            for role, tokens in r.usage.role_breakdown.items():
                fraction = tokens / total_mission_tokens
                role_spend[role] = round(
                    role_spend.get(role, 0.0) + (fraction * r.total_cost_usd), 4
                )

        return LedgerSummary(
            total_missions=len(self._records),
            total_tokens=total_tokens,
            total_spend_usd=round(total_spend, 4),
            total_saved_usd=round(total_saved, 4),
            daily_spend_usd=round(daily_spend, 4),
            spend_by_role=role_spend,
        )
