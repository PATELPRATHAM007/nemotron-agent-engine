"""
Repository Intelligence: Impact Analysis & Scope Lock Subsystem
"""

from app.modules.intelligence.impact.call_graph import CallGraph
from app.modules.intelligence.impact.impact_analyzer import ImpactAnalyzer, ImpactReport
from app.modules.intelligence.impact.scope_lock import ScopeViolationError, TaskScope

__all__ = [
    "CallGraph",
    "ImpactAnalyzer",
    "ImpactReport",
    "ScopeViolationError",
    "TaskScope",
]
