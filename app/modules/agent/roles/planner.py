"""
Planner Role
============
Decomposes high-level mission requests into atomic, verifiable implementation steps.
Identifies relevant features from the knowledge graph and establishes strict task scope boundaries.
"""

from typing import Any

from app.modules.agent.roles.base import AgentRole

PLANNER_SYSTEM_PROMPT = """You are the Lead Architectural Planner Agent for the repository intelligence engine powered by NVIDIA Nemotron 3 Ultra.
Your objective:
1. Decompose the user's objective into atomic, sequentially executable steps.
2. Clearly isolate which files are in PRIMARY scope for modification and which are TEST files.
3. Keep the scope strictly bounded: do NOT include unrelated files.
4. Identify potential breaking changes and architectural risks upfront.
5. Structure your output clearly.
"""


class PlannerRole(AgentRole):
    """Specialized agent role for task planning and scope boundary definition."""

    def __init__(self):
        super().__init__(
            name="Planner",
            system_prompt=PLANNER_SYSTEM_PROMPT,
            allowed_tools=["read_file", "search_code", "list_dir"],
        )

    def build_system_message(self) -> dict[str, str]:
        return {"role": "system", "content": self.system_prompt}

    def build_context_prompt(
        self, goal: str, context: dict[str, Any]
    ) -> list[dict[str, str]]:
        feature_context = context.get("feature_context", "No feature context provided.")
        arch_rules = context.get(
            "architecture_rules", "Follow standard clean architecture."
        )

        user_content = f"""## Mission Goal:
{goal}

## Discovered Feature Context:
{feature_context}

## Architectural Rules:
{arch_rules}

Decompose this task into a structured plan specifying:
1. Target feature name
2. Primary files to modify
3. Test files to create or update
4. Ordered execution steps
5. Potential risks
"""
        return [
            self.build_system_message(),
            {"role": "user", "content": user_content},
        ]
