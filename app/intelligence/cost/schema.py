"""
Token Tracking & Cost Analytics Data Schemas
============================================
Defines domain schemas for token accounting, pricing models, cost breakdowns,
budget guardrails, and persistent financial ledgers.
"""

import time
from enum import Enum

from pydantic import BaseModel, Field


class PricingMode(str, Enum):
    GCP_SPOT = "gcp_spot"
    SERVERLESS_API = "serverless_api"
    HYBRID = "hybrid"


class PricingModel(BaseModel):
    """Configurable rate registry for computing financial spend."""

    mode: PricingMode = PricingMode.GCP_SPOT
    # GCP Spot 8x A100 (~$12.80/hr vs ~$32.77 on-demand)
    gcp_hourly_rate_usd: float = 12.80
    gcp_estimated_throughput_tokens_sec: float = (
        150.0  # aggregate tokens/sec across 8x A100
    )

    # Serverless / Pay-per-token pricing ($ per 1M tokens)
    input_cost_per_million: float = 2.00
    output_cost_per_million: float = 6.00
    reasoning_cost_per_million: float = 4.00

    # Tier-1 Fast Triage (Gemini 2.5 Flash / Jio Plan: $0.00 to $0.075 / 1M tokens)
    tier1_cost_per_million: float = 0.075


class TokenUsageBreakdown(BaseModel):
    """Categorized token counts across inference modalities and agent roles."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    thinking_tokens: int = 0
    total_tokens: int = 0
    role_breakdown: dict[str, int] = Field(default_factory=dict)

    def add(self, other: "TokenUsageBreakdown") -> "TokenUsageBreakdown":
        combined_roles = dict(self.role_breakdown)
        for role, count in other.role_breakdown.items():
            combined_roles[role] = combined_roles.get(role, 0) + count

        return TokenUsageBreakdown(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            thinking_tokens=self.thinking_tokens + other.thinking_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
            role_breakdown=combined_roles,
        )


class CostAlertLevel(str, Enum):
    NORMAL = "NORMAL"
    WARNING_80 = "WARNING_80"
    CRITICAL_95 = "CRITICAL_95"
    EXCEEDED_100 = "EXCEEDED_100"


class MissionCostReport(BaseModel):
    """Complete financial and token telemetry report for a mission."""

    mission_id: str
    target_feature: str = "general"
    pricing_mode: PricingMode = PricingMode.GCP_SPOT
    usage: TokenUsageBreakdown = Field(default_factory=TokenUsageBreakdown)
    duration_seconds: float = 0.0
    total_cost_usd: float = 0.0
    estimated_savings_usd: float = 0.0
    effective_rate_per_1k_tokens_usd: float = 0.0
    alert_level: CostAlertLevel = CostAlertLevel.NORMAL
    timestamp: float = Field(default_factory=time.time)


class CostBudgetConfig(BaseModel):
    """Enforceable spending limits to protect cloud credits and wallets."""

    max_mission_budget_usd: float = 1.00  # Max spend per single coding task
    max_daily_budget_usd: float = 10.00  # Max cumulative spend in 24 hours
    warn_threshold_pct: float = 0.80  # Warn at 80%
    stop_on_budget_exceeded: bool = True  # Circuit breaker activation


class LedgerSummary(BaseModel):
    """Aggregated financial audit statistics."""

    total_missions: int = 0
    total_tokens: int = 0
    total_spend_usd: float = 0.0
    total_saved_usd: float = 0.0
    daily_spend_usd: float = 0.0
    spend_by_role: dict[str, float] = Field(default_factory=dict)
