"""
Cost Module
===========
Provides token cost calculation, persistent ledger tracking, and budget circuit breakers.
"""

from app.modules.cost.service import (
    BudgetGuard,
    CostAlertLevel,
    CostBudgetConfig,
    CostCalculator,
    CostLedger,
    CostRecord,
    CostRepository,
    CostTracker,
    LedgerSummary,
    MissionCostReport,
    PricingMode,
    PricingModel,
    TokenUsageBreakdown,
    budget_guard,
    cost_calculator,
    cost_ledger,
    cost_tracker,
)


def __getattr__(name: str):
    if name == "router":
        from app.modules.cost.router import router
        return router
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "BudgetGuard",
    "budget_guard",
    "CostAlertLevel",
    "CostBudgetConfig",
    "CostCalculator",
    "cost_calculator",
    "CostLedger",
    "cost_ledger",
    "CostRecord",
    "CostRepository",
    "CostTracker",
    "cost_tracker",
    "LedgerSummary",
    "MissionCostReport",
    "PricingMode",
    "PricingModel",
    "TokenUsageBreakdown",
    "router",
]
