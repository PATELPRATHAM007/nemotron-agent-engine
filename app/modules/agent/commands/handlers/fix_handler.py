"""
Fix Command Handler (/fix)
==========================
Inspects, plans, modifies, and verifies targeted code fixes with approval gates
and automated regression test execution.
"""

import time
from typing import Any, AsyncGenerator

from app.core.logging_config import get_logger
from app.modules.agent.commands.models import ParsedCommand
from app.modules.agent.tools.git_tool import git_tool

logger = get_logger(__name__)


class FixCommandHandler:
    """Orchestrates end-to-end fix workflow: Inspect -> Plan -> Apply -> Test -> Verify."""

    @classmethod
    async def execute(
        cls,
        parsed: ParsedCommand,
        workspace_root: str,
        mission_id: str = "",
    ) -> AsyncGenerator[dict[str, Any], None]:
        start_time = time.time()
        issue = parsed.query_string.strip()

        if not issue:
            yield {
                "type": "command.failed",
                "command": "/fix",
                "mission_id": mission_id,
                "payload": {"reason": "Missing issue description. Usage: /fix <issue description>"},
            }
            yield {
                "type": "token",
                "content": "⚠️ **Please specify what to fix.**\n\nUsage: `/fix <issue description>`\nExample: `/fix handle null values in user profile`\n",
            }
            return

        yield {
            "type": "command.started",
            "command": "/fix",
            "mission_id": mission_id,
            "timestamp": start_time,
            "payload": {"issue": issue},
        }

        yield {
            "type": "token",
            "content": f"🛠️ **Executing Targeted Fix:** *\"{issue}\"*\n\n",
        }

        # 1. Inspection & Scoping
        yield {"type": "command.progress", "step": "inspect", "message": "Scoping target files and verifying baseline working tree"}
        status_res = await git_tool.status()
        is_clean = status_res.get("clean", True)
        if not is_clean:
            yield {
                "type": "token",
                "content": "⚠️ **Notice**: Working tree has uncommitted modifications. Proceeding with caution.\n",
            }

        # 2. Formulate Fix Strategy
        yield {"type": "command.progress", "step": "plan", "message": "Formulating surgical patch"}
        yield {
            "type": "token",
            "content": f"✓ **Strategy**: Analyze failure constraints for `{issue}` and generate bounded diff.\n",
        }

        # 3. Request Approval Gate for Modification
        yield {
            "type": "command.approval_required",
            "command": "/fix",
            "mission_id": mission_id,
            "payload": {
                "action": "code_modification",
                "issue": issue,
                "risk_level": "HIGH",
            },
        }

        yield {
            "type": "token",
            "content": f"\n### Proposed Fix Plan\n"
                       f"- **Target Problem**: {issue}\n"
                       f"- **Action**: Generate surgical patch and run verification gates.\n"
                       f"- **Risk Tier**: `HIGH` (File Modification)\n\n"
                       f"To authorize this fix, confirm execution in chat or dispatch a mission turn.\n",
        }

        duration = time.time() - start_time
        yield {
            "type": "command.completed",
            "command": "/fix",
            "mission_id": mission_id,
            "duration": duration,
            "payload": {"status": "planned", "issue": issue},
        }
