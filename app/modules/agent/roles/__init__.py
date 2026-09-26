"""
Specialized Agent Roles Package
===============================
Provides Planner, Reviewer, Coder, Tester, and Debugger roles.
"""

from app.modules.agent.roles.base import (
    AgentRole,
    AgentState,
    CodeChangeOutput,
    DebugHypothesisOutput,
    PlanOutput,
    PlanStep,
    ReviewOutput,
    TestRunOutput,
)
from app.modules.agent.roles.coder import CoderRole
from app.modules.agent.roles.debugger import DebuggerRole
from app.modules.agent.roles.planner import PlannerRole
from app.modules.agent.roles.reviewer import ReviewerRole
from app.modules.agent.roles.tester import TesterRole

__all__ = [
    "AgentRole",
    "AgentState",
    "CodeChangeOutput",
    "CoderRole",
    "DebugHypothesisOutput",
    "DebuggerRole",
    "PlanOutput",
    "PlanStep",
    "PlannerRole",
    "ReviewOutput",
    "ReviewerRole",
    "TestRunOutput",
    "TesterRole",
]
