"""
Database Performance Baseline Engine
====================================
Tracks and persists non-sensitive performance metrics in .agent/memory/performance_baselines.json:
  - Query template execution latency
  - Rows examined vs rows returned ratios
  - Full table scan counts
  - High-latency slow-query warnings
Strictly records metric metadata; never captures raw production user data.
"""

import json
import os
import time
from typing import Any

from pydantic import BaseModel, Field

from app.core.logging_config import get_logger

logger = get_logger(__name__)


class QueryPerformanceMetric(BaseModel):
    query_template: str
    execution_time_ms: float
    rows_examined: int = 0
    rows_returned: int = 0
    index_used: str | None = None
    timestamp: float = Field(default_factory=time.time)


class DatabasePerformanceBaseline:
    """Manages historical query performance benchmarks and bottleneck alerts."""

    def __init__(self, workspace_root: str):
        self.workspace_root = os.path.abspath(workspace_root)
        self.memory_dir = os.path.join(self.workspace_root, ".agent", "memory")
        self.baseline_file = os.path.join(self.memory_dir, "performance_baselines.json")
        self._metrics: list[QueryPerformanceMetric] = []
        self._load()

    def _ensure_dir(self) -> None:
        os.makedirs(self.memory_dir, exist_ok=True)

    def _load(self) -> None:
        if os.path.exists(self.baseline_file):
            try:
                with open(self.baseline_file, encoding="utf-8") as f:
                    data = json.load(f)
                self._metrics = [QueryPerformanceMetric(**item) for item in data]
            except (OSError, json.JSONDecodeError, ValueError) as e:
                logger.error(f"Failed to load performance baselines: {e}")
                self._metrics = []

    def _save(self) -> None:
        self._ensure_dir()
        temp_file = f"{self.baseline_file}.tmp"
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump([m.model_dump() for m in self._metrics], f, indent=2)
            os.replace(temp_file, self.baseline_file)
        except (OSError, TypeError) as e:
            logger.error(f"Failed to save performance baselines: {e}")

    def record_query_metric(
        self,
        query_template: str,
        execution_time_ms: float,
        rows_examined: int = 0,
        rows_returned: int = 0,
        index_used: str | None = None,
    ) -> dict[str, Any]:
        """
        Record a benchmark metric and detect efficiency anomalies.
        """
        metric = QueryPerformanceMetric(
            query_template=query_template,
            execution_time_ms=execution_time_ms,
            rows_examined=rows_examined,
            rows_returned=rows_returned,
            index_used=index_used,
        )
        self._metrics.append(metric)
        # Keep last 500 metrics
        if len(self._metrics) > 500:
            self._metrics = self._metrics[-500:]
        self._save()

        # Anomaly detection
        ratio = rows_examined / max(1, rows_returned)
        is_slow = execution_time_ms > 200.0
        is_inefficient = ratio > 50.0 and rows_examined > 1000

        return {
            "is_slow": is_slow,
            "is_inefficient_scan": is_inefficient,
            "ratio_examined_to_returned": round(ratio, 2),
            "execution_time_ms": execution_time_ms,
        }
