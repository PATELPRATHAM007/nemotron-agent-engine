"""
Cost Module Business Logic Service
==================================
Handles token tracking, cost formulas, budget circuit breaker, and database ledger.
"""

from app.modules.cost.budget_guard import (
    BudgetGuard,
    CostAlertLevel,
    CostBudgetConfig,
)
from app.modules.cost.ledger import (
    CostLedger,
    LedgerSummary,
    MissionCostReport,
)
from app.modules.cost.models import CostRecord
from app.modules.cost.pricing import (
    CostCalculator,
    PricingMode,
    PricingModel,
)
from app.modules.cost.repository import CostRepository
from app.modules.cost.tracker import (
    CostTracker,
    TokenUsageBreakdown,
)

# Shared default singletons
cost_calculator = CostCalculator()
cost_ledger = CostLedger(workspace_root=".")
cost_tracker = CostTracker()
budget_guard = BudgetGuard()

__all__ = [
    "BudgetGuard",
    "CostAlertLevel",
    "CostBudgetConfig",
    "CostCalculator",
    "CostLedger",
    "CostRecord",
    "CostRepository",
    "CostTracker",
    "LedgerSummary",
    "MissionCostReport",
    "PricingMode",
    "PricingModel",
    "TokenUsageBreakdown",
    "budget_guard",
    "cost_calculator",
    "cost_ledger",
    "cost_tracker",
]
