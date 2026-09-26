"""
Real-Time Token Accountant & Usage Tracker
==========================================
Instruments token consumption with sub-category precision (prompt, code, reasoning),
attributes costs to autonomous roles, and computes active financial burn.
"""

import time
from typing import Any

from app.intelligence.context.budget_manager import estimate_tokens
from app.intelligence.cost.pricing import CostCalculator
from app.intelligence.cost.schema import (
    MissionCostReport,
    PricingMode,
    PricingModel,
    TokenUsageBreakdown,
)


class CostTracker:
    """Stateful token and expenditure accumulator for agent sessions and missions."""

    def __init__(self, pricing_model: PricingModel | None = None):
        self.pricing = pricing_model or PricingModel()
        self.calculator = CostCalculator(self.pricing)
        self.start_time: float = time.perf_counter()
        self.offloaded_tokens: int = 0

        # Sub-category counters
        self.prompt_tokens: int = 0
        self.completion_tokens: int = 0
        self.thinking_tokens: int = 0
        self.role_breakdown: dict[str, int] = {}

    def record_prompt(
        self, text_or_messages: str | list[dict[str, Any]], role: str = "Planner"
    ) -> int:
        """Record input prompt tokens before model dispatch."""
        if isinstance(text_or_messages, str):
            token_count = estimate_tokens(text_or_messages)
        else:
            total_text = " ".join(
                m.get("content", "") for m in text_or_messages if isinstance(m, dict)
            )
            token_count = estimate_tokens(total_text)

        self.prompt_tokens += token_count
        self.role_breakdown[role] = self.role_breakdown.get(role, 0) + token_count
        return token_count

    def record_chunk(self, chunk_type: str, content: str, role: str = "Coder") -> int:
        """
        Record a live streaming chunk from Nemotron 3 Ultra.
        Differentiates between reasoning thoughts and code output tokens.
        """
        if not content:
            return 0

        token_count = estimate_tokens(content)
        if chunk_type == "thought":
            self.thinking_tokens += token_count
        else:
            self.completion_tokens += token_count

        self.role_breakdown[role] = self.role_breakdown.get(role, 0) + token_count
        return token_count

    def record_exact_usage(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        thinking_tokens: int = 0,
        role: str = "Coder",
    ) -> None:
        """Overwrite with exact token counts returned from vLLM/NIM response usage headers."""
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.thinking_tokens = thinking_tokens
        self.role_breakdown[role] = prompt_tokens + completion_tokens + thinking_tokens

    def record_tier1_offload(self, prompt_tokens: int) -> None:
        """Record tokens offloaded to Gemini Tier-1 fast router to track savings."""
        self.offloaded_tokens += prompt_tokens

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens + self.thinking_tokens

    def get_breakdown(self) -> TokenUsageBreakdown:
        return TokenUsageBreakdown(
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
            thinking_tokens=self.thinking_tokens,
            total_tokens=self.total_tokens,
            role_breakdown=dict(self.role_breakdown),
        )

    def current_cost(self, mode: PricingMode | None = None) -> float:
        """Compute active financial burn from mission inception to now."""
        elapsed = time.perf_counter() - self.start_time
        return self.calculator.calculate_cost(
            self.get_breakdown(), duration_seconds=elapsed, mode=mode
        )

    def generate_report(
        self,
        mission_id: str,
        target_feature: str = "general",
        mode: PricingMode | None = None,
    ) -> MissionCostReport:
        """Generate final MissionCostReport with telemetry and financial metrics."""
        duration = time.perf_counter() - self.start_time
        return self.calculator.build_report(
            mission_id=mission_id,
            target_feature=target_feature,
            usage=self.get_breakdown(),
            duration_seconds=duration,
            offloaded_tokens=self.offloaded_tokens,
            mode=mode,
        )
