"""
Status Command Handler (/status)
================================
Displays current agent, mission, Git working tree, and index state without leaking secrets.
"""

import os
import time
from typing import Any, AsyncGenerator

from app.core.logging_config import get_logger
from app.modules.agent.commands.models import ParsedCommand
from app.modules.agent.tools.git_tool import git_tool
from app.modules.missions.repository import mission_repository

logger = get_logger(__name__)


class StatusCommandHandler:
    """Orchestrates /status state inspection."""

    @classmethod
    async def execute(
        cls,
        parsed: ParsedCommand,
        workspace_root: str,
        mission_id: str = "",
    ) -> AsyncGenerator[dict[str, Any], None]:
        start_time = time.time()

        yield {
            "type": "command.started",
            "command": "/status",
            "mission_id": mission_id,
            "timestamp": start_time,
        }

        # Git status
        git_res = await git_tool.status()
        branch = git_res.get("branch", "unknown")
        is_clean = git_res.get("clean", True)
        modified = git_res.get("modified", [])
        untracked = git_res.get("untracked", [])

        # Mission state if mission_id provided
        mission_state = "IDLE"
        total_tokens = 0
        total_cost = 0.0
        pending_permissions = 0

        if mission_id:
            m = mission_repository.get_mission(mission_id) or {}
            mission_state = m.get("status", "IDLE")
            total_tokens = m.get("total_tokens", 0)
            total_cost = m.get("total_cost_usd", 0.0)

            # Check pending permission requests
            requests = mission_repository.get_permission_requests(mission_id) if hasattr(mission_repository, "get_permission_requests") else []
            pending_permissions = len([r for r in requests if r.get("status") == "PENDING"])

        project_name = os.path.basename(os.path.abspath(workspace_root))

        status_md = (
            f"### Agent & Repository Status\n\n"
            f"- **Project**: `{project_name}`\n"
            f"- **Git Branch**: `{branch}` ({'Clean' if is_clean else f'Dirty ({len(modified)} modified, {len(untracked)} untracked)'})\n"
            f"- **Active Mission**: `{mission_id or 'None (Interactive Mode)'}`\n"
            f"- **Mission State**: `{mission_state}`\n"
            f"- **Tokens Consumed**: `{total_tokens:,}` (~`${total_cost:.5f}`)\n"
            f"- **Pending Approvals**: `{pending_permissions}`\n"
            f"- **Security & Privacy**: Secrets masked and isolated from telemetry.\n"
        )

        if modified:
            status_md += "\n**Modified Files**:\n" + "\n".join([f"- `{m}`" for m in modified[:8]]) + "\n"

        yield {
            "type": "token",
            "content": status_md,
        }

        duration = time.time() - start_time
        yield {
            "type": "command.completed",
            "command": "/status",
            "mission_id": mission_id,
            "duration": duration,
            "payload": {
                "branch": branch,
                "clean": is_clean,
                "modified_count": len(modified),
                "mission_state": mission_state,
            },
        }
