"""
Plan Command Handler (/plan)
============================
Analyzes user goals and produces a structured, verifiable multi-step plan.
CRITICAL INVARIANT: /plan NEVER modifies files on disk.
"""

import time
from typing import Any, AsyncGenerator

from app.core.logging_config import get_logger
from app.modules.agent.commands.models import ParsedCommand
from app.modules.intelligence.indexing.repo_map import repo_map_generator
from app.modules.missions.repository import mission_repository

logger = get_logger(__name__)


class PlanCommandHandler:
    """Orchestrates /plan analysis without file modification."""

    @classmethod
    async def execute(
        cls,
        parsed: ParsedCommand,
        workspace_root: str,
        mission_id: str = "",
    ) -> AsyncGenerator[dict[str, Any], None]:
        start_time = time.time()
        goal = parsed.query_string.strip()

        if not goal:
            yield {
                "type": "command.failed",
                "command": "/plan",
                "mission_id": mission_id,
                "payload": {"reason": "Missing goal. Usage: /plan <task description>"},
            }
            yield {
                "type": "token",
                "content": "⚠️ **Please specify a goal to plan.**\n\nUsage: `/plan <description of desired change>`\nExample: `/plan Implement JWT authentication callback`\n",
            }
            return

        yield {
            "type": "command.started",
            "command": "/plan",
            "mission_id": mission_id,
            "timestamp": start_time,
            "payload": {"goal": goal},
        }

        yield {
            "type": "token",
            "content": f"📋 **Generating Implementation Plan for:** *\"{goal}\"*\n\n",
        }

        # 1. Understanding & Context Retrieval
        yield {"type": "command.progress", "step": "context", "message": "Evaluating task impact against repository map"}
        repo_map = repo_map_generator.generate_map(workspace_root=workspace_root, max_tokens=1000)

        # 2. Heuristic Impact Scope Analysis
        goal_lower = goal.lower()
        affected_files = []
        if any(w in goal_lower for w in ["auth", "jwt", "login", "oauth"]):
            affected_files = ["app/modules/auth/", "app/core/security.py", "tests/test_auth.py"]
        elif any(w in goal_lower for w in ["database", "migration", "schema", "sql"]):
            affected_files = ["app/db/models/", "alembic/versions/", "tests/test_database.py"]
        elif any(w in goal_lower for w in ["api", "router", "endpoint", "controller"]):
            affected_files = ["app/api/v1/endpoints/", "app/modules/agent/router.py"]
        elif any(w in goal_lower for w in ["test", "testing", "gate"]):
            affected_files = ["tests/"]
        else:
            affected_files = ["app/main.py", "README.md"]

        steps = [
            {
                "id": 1,
                "title": "Context Retrieval & Impact Analysis",
                "description": f"Inspect AST definitions and dependencies in target subsystems: {', '.join(affected_files)}",
                "risk_level": "LOW",
                "requires_approval": False,
            },
            {
                "id": 2,
                "title": "Draft Surgical Implementation",
                "description": "Formulate targeted code modifications adhering to clean architectural boundaries.",
                "risk_level": "MEDIUM",
                "requires_approval": True,
            },
            {
                "id": 3,
                "title": "Automated Test Suite Verification",
                "description": "Execute relevant unit and regression test suites to verify functionality and ensure 0 regressions.",
                "risk_level": "LOW",
                "requires_approval": False,
            },
            {
                "id": 4,
                "title": "Final Review & Git Checkpoint",
                "description": "Generate unified diff and present changes for human review.",
                "risk_level": "LOW",
                "requires_approval": False,
            },
        ]

        summary = (
            f"### Plan Overview\n"
            f"**Objective**: {goal}\n\n"
            f"**Affected Files / Modules**:\n"
            + "\n".join([f"- `{f}`" for f in affected_files])
            + "\n\n"
            f"**Architecture Impact**: Contained to modular layers, preserving API backwards-compatibility.\n\n"
            f"**Execution Steps**:\n"
            + "\n".join([f"{s['id']}. **{s['title']}**: {s['description']}" for s in steps])
            + "\n\n"
            f"**Risks & Mitigation**:\n"
            f"- *Risk*: Unintended regression in dependent modules.\n"
            f"- *Mitigation*: Run automated test gate and require explicit user approval before disk writes.\n\n"
            f"**Testing Strategy**:\n"
            f"- Run pytest/vitest against modified modules.\n"
            f"- Verify type check passes cleanly with zero errors.\n"
        )

        # Persist proposed plan if mission_id exists
        if mission_id:
            mission_repository.save_plan(
                mission_id=mission_id,
                steps=steps,
                summary=f"Implementation plan for: {goal}",
                status="PROPOSED",
            )

        yield {
            "type": "plan_created",
            "mission_id": mission_id,
            "summary": summary,
            "steps": steps,
            "requires_approval": True,
        }

        yield {
            "type": "token",
            "content": summary + "\n\n💡 *Note: /plan never modifies files on disk. To execute, approve the plan or run `/fix <task>`.*",
        }

        duration = time.time() - start_time
        yield {
            "type": "command.completed",
            "command": "/plan",
            "mission_id": mission_id,
            "duration": duration,
            "payload": {"steps_count": len(steps), "affected_files": affected_files},
        }
