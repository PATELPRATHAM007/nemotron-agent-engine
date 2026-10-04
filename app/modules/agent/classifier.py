"""
Dynamic Task Classifier
=======================
Classifies user requests into discrete agent workflows:
  - QUESTION: Direct conversational answer without workspace modifications.
  - RESEARCH: Read-only exploration of repository, dependencies, and documentation.
  - PLAN: Architecture evaluation with Option A / B / C tradeoffs and roadmap.
  - BUILD: Full autonomous engineering lifecycle (modify code, add tests, verify).
  - DEBUG: Stack-trace diagnosis, reproducing errors, and applying targeted fixes.
  - REVIEW: Static analysis, diff review, and constitutional security audit.
"""

import re
from enum import Enum

from pydantic import BaseModel, Field

from app.core.logging_config import get_logger

logger = get_logger(__name__)


class TaskWorkflow(str, Enum):
    QUESTION = "QUESTION"
    RESEARCH = "RESEARCH"
    PLAN = "PLAN"
    BUILD = "BUILD"
    DEBUG = "DEBUG"
    REVIEW = "REVIEW"


class ClassificationResult(BaseModel):
    workflow: TaskWorkflow
    confidence: float = Field(ge=0.0, le=1.0)
    recommended_subagent: str
    requires_workspace_write: bool
    requires_test_run: bool
    allowed_tools: list[str] = Field(default_factory=list)
    rationale: str


class DynamicTaskClassifier:
    """
    Evaluates user prompts and determines the optimal agent workflow,
    recommended subagents, and tool permissions.
    """

    # Keyword and regex patterns for workflow classification
    DEBUG_PATTERNS = [
        r"\b(?:fix|debug|resolve|diagnose)\b.*(?:error|bug|issue|exception|failure|crash|traceback|500)",
        r"\b(?:traceback|assertionerror|typeerror|valueerror|keyerror|importerror|indexerror)\b",
        r"\btest(?:s)?\s+(?:is|are)?\s*(?:failing|broken|crashing)\b",
        r"\bwhy\s+is\s+it\s+(?:failing|crashing|throwing)\b",
    ]

    REVIEW_PATTERNS = [
        r"\b(?:review|audit|inspect|check)\b.*(?:diff|pr|commit|changes|branch|code\s+quality|security)",
        r"\b(?:security|vulnerability|audit)\s+review\b",
        r"\blint\b",
        r"\bcheck\s+for\s+(?:vulnerabilities|regressions|code\s+smells)\b",
    ]

    PLAN_PATTERNS = [
        r"\b(?:plan|roadmap|architect|design)\b.*(?:architecture|migration|strategy|feature|system)",
        r"\b(?:how\s+should\s+we|what\s+is\s+the\s+best\s+way\s+to)\s+(?:architect|structure|design|migrate)\b",
        r"\bcompare\s+options\b",
        r"\boption\s+[abc]\b",
        r"\btradeoffs?\b",
    ]

    RESEARCH_PATTERNS = [
        r"\b(?:find|search|locate|where\s+is|trace|explore|list\s+all)\b.*(?:endpoint|class|function|usage|reference|file)",
        r"\bhow\s+does\s+(?:the\s+)?.*work\b",
        r"\bwhere\s+is\s+.*defined\b",
        r"\bwhich\s+files\s+(?:handle|contain|import)\b",
    ]

    BUILD_PATTERNS = [
        r"\b(?:create|implement|add|build|generate|refactor|update|write|modify|mount)\b.*(?:endpoint|api|route|service|model|component|feature|test|module)",
        r"\bwire\s+up\b",
        r"\badd\s+support\s+for\b",
        r"\bmake\s+changes\b",
    ]

    QUESTION_PATTERNS = [
        r"^(?:hi|hello|hey|good\s+morning|good\s+evening|greetings|howdy|sup|yo|thanks|thank\s+you)\b",
        r"\bwhat\s+is\b",
        r"\bcan\s+you\s+explain\b",
        r"\btell\s+me\s+about\b",
        r"\bwhat\s+does\s+.*mean\b",
    ]

    def classify(self, prompt: str) -> ClassificationResult:
        """
        Classifies user prompt into the most appropriate TaskWorkflow.
        """
        text = prompt.strip() if prompt else ""
        if not text:
            return ClassificationResult(
                workflow=TaskWorkflow.QUESTION,
                confidence=1.0,
                recommended_subagent="DirectResponder",
                requires_workspace_write=False,
                requires_test_run=False,
                allowed_tools=["read_file", "get_repo_map"],
                rationale="Empty prompt received; defaulting to conversational QUESTION response.",
            )

        lower = text.lower()


        # 1. Check DEBUG patterns
        for pattern in self.DEBUG_PATTERNS:
            if re.search(pattern, lower):
                return ClassificationResult(
                    workflow=TaskWorkflow.DEBUG,
                    confidence=0.92,
                    recommended_subagent="DebuggerSubagent",
                    requires_workspace_write=True,
                    requires_test_run=True,
                    allowed_tools=["read_file", "edit_file", "apply_diff_patch", "execute_command", "run_process", "ripgrep_search", "git_tool"],
                    rationale=f"Prompt indicates active bug, exception, or test failure: matched '{pattern}'.",
                )

        # 2. Check REVIEW patterns
        for pattern in self.REVIEW_PATTERNS:
            if re.search(pattern, lower):
                return ClassificationResult(
                    workflow=TaskWorkflow.REVIEW,
                    confidence=0.90,
                    recommended_subagent="ReviewerSubagent",
                    requires_workspace_write=False,
                    requires_test_run=True,
                    allowed_tools=["read_file", "ripgrep_search", "git_tool", "get_git_history", "run_process"],
                    rationale=f"Prompt requests static code analysis, diff inspection, or security audit: matched '{pattern}'.",
                )

        # 3. Check PLAN patterns
        for pattern in self.PLAN_PATTERNS:
            if re.search(pattern, lower):
                return ClassificationResult(
                    workflow=TaskWorkflow.PLAN,
                    confidence=0.88,
                    recommended_subagent="PlannerSubagent",
                    requires_workspace_write=False,
                    requires_test_run=False,
                    allowed_tools=["read_file", "ripgrep_search", "get_repo_map", "list_dir"],
                    rationale=f"Prompt requests architectural evaluation or multi-stage planning: matched '{pattern}'.",
                )

        # 4. Check BUILD patterns
        for pattern in self.BUILD_PATTERNS:
            if re.search(pattern, lower):
                return ClassificationResult(
                    workflow=TaskWorkflow.BUILD,
                    confidence=0.90,
                    recommended_subagent="CoderSubagent",
                    requires_workspace_write=True,
                    requires_test_run=True,
                    allowed_tools=["read_file", "write_file", "edit_file", "apply_diff_patch", "execute_command", "run_process", "ripgrep_search", "git_tool"],
                    rationale=f"Prompt requests new feature implementation or code modification: matched '{pattern}'.",
                )

        # 5. Check RESEARCH patterns
        for pattern in self.RESEARCH_PATTERNS:
            if re.search(pattern, lower):
                return ClassificationResult(
                    workflow=TaskWorkflow.RESEARCH,
                    confidence=0.85,
                    recommended_subagent="ResearcherSubagent",
                    requires_workspace_write=False,
                    requires_test_run=False,
                    allowed_tools=["read_file", "ripgrep_search", "get_repo_map", "list_dir", "get_git_history"],
                    rationale=f"Prompt asks to find, locate, or trace code/endpoints: matched '{pattern}'.",
                )

        # 6. Check QUESTION patterns
        for pattern in self.QUESTION_PATTERNS:
            if re.search(pattern, lower):
                return ClassificationResult(
                    workflow=TaskWorkflow.QUESTION,
                    confidence=0.88,
                    recommended_subagent="DirectResponder",
                    requires_workspace_write=False,
                    requires_test_run=False,
                    allowed_tools=["read_file", "get_repo_map"],
                    rationale=f"Prompt is a conversational question or greeting: matched '{pattern}'.",
                )

        # Fallback heuristic
        if "?" in lower and len(lower.split()) < 25:
            return ClassificationResult(
                workflow=TaskWorkflow.QUESTION,
                confidence=0.75,
                recommended_subagent="DirectResponder",
                requires_workspace_write=False,
                requires_test_run=False,
                allowed_tools=["read_file", "get_repo_map"],
                rationale="Prompt contains question mark and is concise; defaulting to QUESTION.",
            )

        # If it looks like an action command without explicit patterns
        return ClassificationResult(
            workflow=TaskWorkflow.BUILD,
            confidence=0.70,
            recommended_subagent="CoderSubagent",
            requires_workspace_write=True,
            requires_test_run=True,
            allowed_tools=["read_file", "write_file", "edit_file", "apply_diff_patch", "execute_command", "run_process", "ripgrep_search"],
            rationale="Prompt represents a general engineering task; defaulting to BUILD.",
        )


task_classifier = DynamicTaskClassifier()
