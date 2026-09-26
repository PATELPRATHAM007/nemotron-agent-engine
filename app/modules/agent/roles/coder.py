"""
Coder Role
==========
Executes targeted code changes, refactors, and implementations strictly within
the bounds of the authorized TaskScope and within the <= 32k token context ceiling.
"""

from typing import Any

from app.modules.agent.roles.base import AgentRole

CODER_SYSTEM_PROMPT = """You are the Principal Software Engineer (Coder Agent) powered by NVIDIA Nemotron 3 Ultra (550B LatentMoE).
Your strengths include writing clean, robust, type-annotated, idiomatic code and precise surgical diffs.

Mandatory Constraints:
1. STRICT SCOPE LOCK: You may ONLY write to authorized primary files in this task scope. Writing to unauthorized files is strictly forbidden.
2. DO NOT hallucinate imports or dependencies. Rely on provided signatures.
3. Preserve all existing docstrings, public interfaces, and comments unless explicitly instructed otherwise.
4. Always handle edge cases, error conditions, and nullability.
5. Provide code diffs or complete file contents using tools cleanly.
"""


class CoderRole(AgentRole):
    """Specialized agent role for safe, scope-bound code generation."""

    def __init__(self):
        super().__init__(
            name="Coder",
            system_prompt=CODER_SYSTEM_PROMPT,
            allowed_tools=["read_file", "write_file", "replace_content", "search_code"],
        )

    def build_system_message(self) -> dict[str, str]:
        return {"role": "system", "content": self.system_prompt}

    def build_context_prompt(
        self, goal: str, context: dict[str, Any]
    ) -> list[dict[str, str]]:
        step_description = context.get("current_step", goal)
        target_files = context.get("target_files", [])
        dep_signatures = context.get("dependency_signatures", "")
        existing_code = context.get("existing_code", "")
        lessons = context.get("historical_lessons", "")

        user_content = f"""## Active Task Step:
{step_description}

## Authorized Target Files:
{", ".join(target_files) if target_files else "None authorized"}

## Dependency Signatures (Reference Only - Do Not Modify):
{dep_signatures}

## Existing Code Context:
{existing_code}

## Historical Lessons & Past Fixes:
{lessons}

Implement the requested changes with high quality and adherence to repository style.
"""
        return [
            self.build_system_message(),
            {"role": "user", "content": user_content},
        ]
