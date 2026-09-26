"""
Tester Role
===========
Generates comprehensive unit and integration tests and executes the test suite
to verify correctness, edge case handling, and regression safety.
"""

from typing import Any

from app.modules.agent.roles.base import AgentRole

TESTER_SYSTEM_PROMPT = """You are the Senior QA & Test Automation Agent powered by NVIDIA Nemotron 3 Ultra.
Your objective:
1. Formulate rigorous unit and integration tests using pytest and modern testing patterns.
2. Assert boundary values, failure paths, null safety, and exception handling.
3. Validate that existing system behavior has not regressed.
4. Execute tests in the isolated verification environment and report structured results.
"""


class TesterRole(AgentRole):
    """Specialized agent role for test generation and test suite execution."""

    __test__ = False

    def __init__(self):
        super().__init__(
            name="Tester",
            system_prompt=TESTER_SYSTEM_PROMPT,
            allowed_tools=["read_file", "write_file", "run_terminal", "search_code"],
        )

    def build_system_message(self) -> dict[str, str]:
        return {"role": "system", "content": self.system_prompt}

    def build_context_prompt(
        self, goal: str, context: dict[str, Any]
    ) -> list[dict[str, str]]:
        target_files = context.get("target_files", [])
        test_files = context.get("test_files", [])
        code_diff = context.get("code_diff", "")

        user_content = f"""## Mission Verification Objective:
{goal}

## Files Modified:
{", ".join(target_files)}

## Target Test Files:
{", ".join(test_files) if test_files else "New test file needed"}

## Applied Code Changes:
{code_diff}

Generate or update test cases to thoroughly verify these changes and assert boundary conditions.
"""
        return [
            self.build_system_message(),
            {"role": "user", "content": user_content},
        ]
