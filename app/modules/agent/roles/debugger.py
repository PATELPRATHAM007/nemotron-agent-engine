"""
Debugger Role
=============
Invoked strictly upon verification failure (test errors, lint breaks, gate violations).
Analyzes failure traces, pinpoints root causes, and generates precise repair hypotheses.
Hard-bounded by max_auto_fix_attempts (default 3) to prevent infinite loops.
"""

from typing import Any

from app.modules.agent.roles.base import AgentRole

DEBUGGER_SYSTEM_PROMPT = """You are the Lead Systems Debugger & Root Cause Specialist powered by NVIDIA Nemotron 3 Ultra.
Your objective:
1. Carefully diagnose the failure trace, assertion failure, or syntax error.
2. Formulate a precise hypothesis explaining WHY the failure occurred.
3. Propose the minimal surgical change required to fix the root cause.
4. DO NOT make broad or speculative changes. Keep fixes localized and targeted.
"""


class DebuggerRole(AgentRole):
    """Specialized agent role for bounded root-cause diagnosis and repair formulation."""

    def __init__(self, max_attempts: int = 3):
        super().__init__(
            name="Debugger",
            system_prompt=DEBUGGER_SYSTEM_PROMPT,
            allowed_tools=["read_file", "search_code"],
        )
        self.max_attempts = max_attempts

    def build_system_message(self) -> dict[str, str]:
        return {"role": "system", "content": self.system_prompt}

    def build_context_prompt(
        self, goal: str, context: dict[str, Any]
    ) -> list[dict[str, str]]:
        failure_trace = context.get("failure_trace", "No trace provided.")
        attempt = context.get("attempt_number", 1)
        target_files = context.get("target_files", [])

        user_content = f"""## Mission Objective:
{goal}

## Failure Diagnosed (Attempt {attempt}/{self.max_attempts}):
{failure_trace}

## Target Files In-Scope:
{", ".join(target_files)}

Diagnose the root cause and provide a specific, surgical remediation plan.
"""
        return [
            self.build_system_message(),
            {"role": "user", "content": user_content},
        ]
