"""
Context Budget & Progressive Expansion Module
=============================================
Manages token allocation, hierarchical prompt assembly, and evidence ranking.
"""

from app.modules.intelligence.context.budget_allocator import (
    ContextBudgetAllocator,
    ContextLayer,
    LayerAllocationResult,
    LayeredContextBudgetConfig,
    LayerQuotas,
)
from app.modules.intelligence.context.budget_manager import (
    ContextBudget,
    ContextBudgetManager,
    estimate_tokens,
    truncate_to_tokens,
)
from app.modules.intelligence.context.compactor import (
    ContextCompactor,
    ContextPressureLevel,
    ToolResultPolicy,
)
from app.modules.intelligence.context.hierarchical import HierarchicalContextBuilder
from app.modules.intelligence.context.ranker import ContextRanker

__all__ = [
    "ContextBudget",
    "ContextBudgetAllocator",
    "ContextBudgetManager",
    "ContextCompactor",
    "ContextLayer",
    "ContextPressureLevel",
    "ContextRanker",
    "HierarchicalContextBuilder",
    "LayerAllocationResult",
    "LayerQuotas",
    "LayeredContextBudgetConfig",
    "ToolResultPolicy",
    "estimate_tokens",
    "truncate_to_tokens",
]

