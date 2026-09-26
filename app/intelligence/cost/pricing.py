"""
Pricing Engine & Savings Calculator
===================================
Calculates dollar expenditures and cost savings across GCP Spot GPU compute,
serverless pay-per-token inference, and hybrid Tier-1 router offloading.
"""

from app.intelligence.cost.schema import (
    MissionCostReport,
    PricingMode,
    PricingModel,
    TokenUsageBreakdown,
)


class CostCalculator:
    """Calculates granular expenditures across multiple pricing topologies."""

    def __init__(self, pricing_model: PricingModel | None = None):
        self.pricing = pricing_model or PricingModel()

    def calculate_cost(
        self,
        usage: TokenUsageBreakdown,
        duration_seconds: float = 0.0,
        mode: PricingMode | None = None,
    ) -> float:
        """
        Calculate total financial spend for a token breakdown.
        """
        active_mode = mode or self.pricing.mode

        if active_mode == PricingMode.GCP_SPOT:
            # GCP Spot instance cost model
            if duration_seconds > 0:
                cost = (duration_seconds / 3600.0) * self.pricing.gcp_hourly_rate_usd
            else:
                # Amortized per token using throughput estimate
                tokens_per_hour = (
                    self.pricing.gcp_estimated_throughput_tokens_sec * 3600.0
                )
                cost = (
                    usage.total_tokens / max(1.0, tokens_per_hour)
                ) * self.pricing.gcp_hourly_rate_usd
            return round(cost, 6)

        elif active_mode == PricingMode.SERVERLESS_API:
            # Per-million token API rates
            prompt_cost = (
                usage.prompt_tokens / 1_000_000.0
            ) * self.pricing.input_cost_per_million
            comp_cost = (
                usage.completion_tokens / 1_000_000.0
            ) * self.pricing.output_cost_per_million
            think_cost = (
                usage.thinking_tokens / 1_000_000.0
            ) * self.pricing.reasoning_cost_per_million
            return round(prompt_cost + comp_cost + think_cost, 6)

        else:  # HYBRID
            # Uses Spot compute for coding + Serverless rates for validation
            spot_cost = (
                (duration_seconds / 3600.0) * self.pricing.gcp_hourly_rate_usd
                if duration_seconds > 0
                else 0.0
            )
            api_cost = (
                usage.completion_tokens / 1_000_000.0
            ) * self.pricing.output_cost_per_million
            return round(spot_cost + api_cost, 6)

    def calculate_tier1_savings(self, offloaded_prompt_tokens: int) -> float:
        """
        Calculate dollars saved by routing routine triage tasks to Google Gemini
        ($0.075/1M or $0 free) instead of the 550B Nemotron frontier model ($2.00/1M).
        """
        nemotron_cost = (
            offloaded_prompt_tokens / 1_000_000.0
        ) * self.pricing.input_cost_per_million
        gemini_cost = (
            offloaded_prompt_tokens / 1_000_000.0
        ) * self.pricing.tier1_cost_per_million
        return max(0.0, round(nemotron_cost - gemini_cost, 6))

    def build_report(
        self,
        mission_id: str,
        target_feature: str,
        usage: TokenUsageBreakdown,
        duration_seconds: float,
        offloaded_tokens: int = 0,
        mode: PricingMode | None = None,
    ) -> MissionCostReport:
        """Build a comprehensive MissionCostReport with telemetry and rate calculations."""
        active_mode = mode or self.pricing.mode
        cost = self.calculate_cost(
            usage, duration_seconds=duration_seconds, mode=active_mode
        )
        savings = self.calculate_tier1_savings(offloaded_tokens)

        # Rate per 1,000 tokens
        effective_rate = (cost / max(1, usage.total_tokens)) * 1000.0

        return MissionCostReport(
            mission_id=mission_id,
            target_feature=target_feature,
            pricing_mode=active_mode,
            usage=usage,
            duration_seconds=round(duration_seconds, 2),
            total_cost_usd=round(cost, 4),
            estimated_savings_usd=round(savings, 4),
            effective_rate_per_1k_tokens_usd=round(effective_rate, 6),
        )
