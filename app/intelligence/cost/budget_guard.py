"""
Economic Circuit Breaker & Budget Guardrail
===========================================
Protects developer budgets and cloud credits by enforcing hard cost ceilings
on individual missions and 24-hour cumulative spend.
"""

from app.core.exceptions import CostBudgetExceededError
from app.core.logging_config import get_logger
from app.intelligence.cost.schema import (
    CostAlertLevel,
    CostBudgetConfig,
    PricingMode,
)
from app.intelligence.cost.tracker import CostTracker

logger = get_logger(__name__)


class BudgetGuard:
    """Enforces financial ceilings and circuit-breaker halts on agent execution."""

    def __init__(self, config: CostBudgetConfig | None = None):
        self.config = config or CostBudgetConfig()

    def check_mission_budget(
        self,
        tracker: CostTracker,
        mode: PricingMode | None = None,
        daily_accumulated_spend: float = 0.0,
    ) -> CostAlertLevel:
        """
        Validate active expenditure against mission and daily limits.
        Raises CostBudgetExceededError if threshold breached and stop_on_budget_exceeded is True.
        """
        current_mission_cost = tracker.current_cost(mode=mode)
        total_daily_cost = daily_accumulated_spend + current_mission_cost

        # 1. Check Mission Limit
        if current_mission_cost >= self.config.max_mission_budget_usd:
            logger.error(
                f"🛑 Budget Guardrail Triggered: Mission spend (${current_mission_cost:.4f}) "
                f"reached limit (${self.config.max_mission_budget_usd:.2f})"
            )
            if self.config.stop_on_budget_exceeded:
                raise CostBudgetExceededError(
                    f"Mission budget limit exceeded: ${current_mission_cost:.4f} >= ${self.config.max_mission_budget_usd:.2f}.",
                    current_cost_usd=current_mission_cost,
                    max_cost_usd=self.config.max_mission_budget_usd,
                )
            return CostAlertLevel.EXCEEDED_100

        # 2. Check Daily Limit
        if total_daily_cost >= self.config.max_daily_budget_usd:
            logger.error(
                f"🛑 Budget Guardrail Triggered: Daily spend (${total_daily_cost:.4f}) "
                f"reached limit (${self.config.max_daily_budget_usd:.2f})"
            )
            if self.config.stop_on_budget_exceeded:
                raise CostBudgetExceededError(
                    f"Daily spending limit exceeded: ${total_daily_cost:.4f} >= ${self.config.max_daily_budget_usd:.2f}.",
                    current_cost_usd=total_daily_cost,
                    max_cost_usd=self.config.max_daily_budget_usd,
                )
            return CostAlertLevel.EXCEEDED_100

        # 3. Warning Thresholds
        mission_ratio = current_mission_cost / max(
            0.01, self.config.max_mission_budget_usd
        )
        daily_ratio = total_daily_cost / max(0.01, self.config.max_daily_budget_usd)
        highest_ratio = max(mission_ratio, daily_ratio)

        if highest_ratio >= 0.95:
            logger.warning(
                f"⚠️ Critical Cost Alert: Spent {highest_ratio * 100:.1f}% of budget."
            )
            return CostAlertLevel.CRITICAL_95
        elif highest_ratio >= self.config.warn_threshold_pct:
            logger.warning(
                f"⚠️ Budget Warning: Spent {highest_ratio * 100:.1f}% of budget threshold."
            )
            return CostAlertLevel.WARNING_80

        return CostAlertLevel.NORMAL
