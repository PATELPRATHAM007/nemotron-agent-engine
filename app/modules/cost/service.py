"""
Cost Module Business Logic Service
==================================
Handles token tracking, cost formulas, budget circuit breaker, and database ledger.
"""

from app.intelligence.cost import (
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
)

# Shared default singletons
cost_calculator = CostCalculator()
cost_ledger = CostLedger(workspace_root=".")
cost_tracker = CostTracker()
budget_guard = BudgetGuard()

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
]
