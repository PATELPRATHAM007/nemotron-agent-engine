"""
Context Budget Manager
=======================
Strictly bounds model prompt context to a <= 32,000 token ceiling, dynamically
allocating token slices across system instructions, task rules, feature graphs,
source code, tests, and historical lessons.
"""

from typing import Any

from pydantic import BaseModel


class ContextBudget(BaseModel):
    """Dynamic token allocation quotas."""

    max_total_tokens: int = 32000
    system_role: int = 1500
    task_rules: int = 1000
    architecture_adrs: int = 2000
    feature_subgraph: int = 2500
    target_code: int = 15000
    tests: int = 5000
    lessons: int = 2000
    tool_buffer: int = 3000


def estimate_tokens(text: str) -> int:
    """Fast, accurate token estimation heuristic (~3.8 chars per token for code/text)."""
    if not text:
        return 0
    return max(1, int(len(text) / 3.8))


def truncate_to_tokens(
    text: str,
    max_tokens: int,
    suffix: str = "\n... [truncated to fit context budget] ...",
) -> str:
    """Trim string to strictly fit within token ceiling."""
    current_tokens = estimate_tokens(text)
    if current_tokens <= max_tokens:
        return text

    # Approximate character limit
    char_limit = int(max_tokens * 3.8) - len(suffix)
    if char_limit <= 0:
        return text[: max_tokens * 3]
    return text[:char_limit] + suffix


class ContextBudgetManager:
    """Enforces token boundaries on constructed prompt components."""

    def __init__(self, budget: ContextBudget | None = None):
        self.budget = budget or ContextBudget()

    def assemble_payload(
        self,
        system_instructions: str,
        task_prompt: str,
        architecture_context: str,
        feature_subgraph_str: str,
        target_code: str,
        test_context: str,
        lessons_context: str,
    ) -> dict[str, Any]:
        """
        Assemble and truncate all context sections to guarantee total payload <= 32k tokens.
        """
        trimmed_system = truncate_to_tokens(
            system_instructions, self.budget.system_role
        )
        trimmed_task = truncate_to_tokens(task_prompt, self.budget.task_rules)
        trimmed_arch = truncate_to_tokens(
            architecture_context, self.budget.architecture_adrs
        )
        trimmed_graph = truncate_to_tokens(
            feature_subgraph_str, self.budget.feature_subgraph
        )
        trimmed_code = truncate_to_tokens(target_code, self.budget.target_code)
        trimmed_tests = truncate_to_tokens(test_context, self.budget.tests)
        trimmed_lessons = truncate_to_tokens(lessons_context, self.budget.lessons)

        token_usage = {
            "system_role": estimate_tokens(trimmed_system),
            "task_rules": estimate_tokens(trimmed_task),
            "architecture": estimate_tokens(trimmed_arch),
            "feature_graph": estimate_tokens(trimmed_graph),
            "target_code": estimate_tokens(trimmed_code),
            "tests": estimate_tokens(trimmed_tests),
            "lessons": estimate_tokens(trimmed_lessons),
        }
        total_tokens = sum(token_usage.values())

        return {
            "system_role": trimmed_system,
            "task_rules": trimmed_task,
            "architecture": trimmed_arch,
            "feature_graph": trimmed_graph,
            "target_code": trimmed_code,
            "tests": trimmed_tests,
            "lessons": trimmed_lessons,
            "token_usage": token_usage,
            "total_tokens": total_tokens,
            "within_budget": total_tokens <= self.budget.max_total_tokens,
        }

    def assert_within_budget(self, total_tokens: int) -> None:
        """
        Asserts total token count does not exceed the model context budget.
        Raises ContextBudgetExceededError with diagnostic details if ceiling breached.
        """
        from app.core.exceptions import ContextBudgetExceededError

        if total_tokens > self.budget.max_total_tokens:
            raise ContextBudgetExceededError(
                f"Context budget ceiling exceeded: {total_tokens} tokens > {self.budget.max_total_tokens} tokens maximum.",
                token_count=total_tokens,
                max_tokens=self.budget.max_total_tokens,
            )
