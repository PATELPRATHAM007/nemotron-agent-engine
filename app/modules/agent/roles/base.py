"""
Base Agent Role Specification
=============================
Defines the abstract interface and standard data structures for specialized roles:
Planner, Reviewer, Coder, Tester, Debugger.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AgentState(str, Enum):
    """Finite State Machine states for the autonomous orchestrator."""

    IDLE = "IDLE"
    PLANNING = "PLANNING"
    REVIEWING = "REVIEWING"
    CODING = "CODING"
    TESTING = "TESTING"
    DEBUGGING = "DEBUGGING"
    COMMITTING = "COMMITTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"


class PlanStep(BaseModel):
    step_id: int
    title: str
    description: str
    target_files: list[str] = Field(default_factory=list)
    action: str  # e.g., "create", "modify", "test"


class PlanOutput(BaseModel):
    summary: str
    target_feature: str
    primary_files: list[str] = Field(default_factory=list)
    test_files: list[str] = Field(default_factory=list)
    steps: list[PlanStep] = Field(default_factory=list)
    risks_identified: list[str] = Field(default_factory=list)


class ReviewOutput(BaseModel):
    approved: bool
    critique: str
    scope_violations: list[str] = Field(default_factory=list)
    token_budget_compliant: bool = True
    suggested_modifications: list[str] = Field(default_factory=list)


class CodeChangeOutput(BaseModel):
    modified_files: list[str] = Field(default_factory=list)
    diff_summary: str = ""
    notes: str = ""


class TestRunOutput(BaseModel):
    __test__ = False
    passed: bool
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    failure_trace: str | None = None
    output_log: str = ""


class DebugHypothesisOutput(BaseModel):
    attempt_number: int
    root_cause: str
    proposed_fix: str
    files_to_modify: list[str] = Field(default_factory=list)


class AgentRole(ABC):
    """Abstract base class for specialized agent roles."""

    def __init__(
        self, name: str, system_prompt: str, allowed_tools: list[str] | None = None
    ):
        self.name = name
        self.system_prompt = system_prompt
        self.allowed_tools = allowed_tools or []

    @abstractmethod
    def build_system_message(self) -> dict[str, str]:
        """Construct the role-specific system prompt."""
        return {"role": "system", "content": self.system_prompt}

    @abstractmethod
    def build_context_prompt(
        self, goal: str, context: dict[str, Any]
    ) -> list[dict[str, str]]:
        """Assemble structured conversation messages for the LLM gateway."""
