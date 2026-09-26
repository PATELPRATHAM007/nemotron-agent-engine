"""
Cost & Token Analytics Pydantic Schemas
=======================================
Request & response models for token accounting, metrics, and budget tracking.
"""

from typing import Any
from pydantic import BaseModel, Field


class CostRecordSchema(BaseModel):
    id: str
    mission_id: str
    session_id: str
    phase: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    model_name: str
    created_at: str | None = None


class CostSummaryResponse(BaseModel):
    total_records: int
    total_tokens: int
    total_cost_usd: float
    by_phase: dict[str, Any]
    by_model: dict[str, Any]


class BudgetCheckPayload(BaseModel):
    mission_id: str
    additional_tokens: int = 0
    additional_cost_usd: float = 0.0
