"""
Diff Command Handler (/diff)
============================
Displays structured Git diff: files changed, additions, deletions, and risk assessment.
"""

import time
from typing import Any, AsyncGenerator

from app.core.logging_config import get_logger
from app.modules.agent.commands.models import ParsedCommand
from app.modules.agent.tools.git_tool import git_tool

logger = get_logger(__name__)


class DiffCommandHandler:
    """Orchestrates /diff working tree comparison."""

    @classmethod
    async def execute(
        cls,
        parsed: ParsedCommand,
        workspace_root: str,
        mission_id: str = "",
    ) -> AsyncGenerator[dict[str, Any], None]:
        start_time = time.time()
        target_path = parsed.query_string.strip() or None

        yield {
            "type": "command.started",
            "command": "/diff",
            "mission_id": mission_id,
            "timestamp": start_time,
            "payload": {"target_path": target_path},
        }

        diff_res = await git_tool.diff(filepath=target_path)
        diff_text = diff_res.get("diff", "").strip()

        if not diff_text:
            yield {
                "type": "token",
                "content": "✓ **No uncommitted changes.** Working tree is completely clean.\n",
            }
            yield {
                "type": "command.completed",
                "command": "/diff",
                "mission_id": mission_id,
                "duration": time.time() - start_time,
                "payload": {"status": "clean"},
            }
            return

        lines = diff_text.splitlines()
        added = len([l for l in lines if l.startswith("+") and not l.startswith("+++")])
        removed = len([l for l in lines if l.startswith("-") and not l.startswith("---")])

        yield {
            "type": "diff_generated",
            "diff": diff_text[:8000],
            "file_path": target_path or "working_tree",
        }

        summary_md = (
            f"### Working Tree Diff\n\n"
            f"- **Additions**: `+{added:,}` lines\n"
            f"- **Deletions**: `-{removed:,}` lines\n"
            f"- **Target**: `{target_path or 'Entire Repository'}`\n\n"
            f"```diff\n"
            f"{diff_text[:3000]}\n"
            + (f"\n... ({len(lines) - 50} more lines truncated for chat view)" if len(lines) > 50 else "")
            + f"\n```\n"
        )

        yield {
            "type": "token",
            "content": summary_md,
        }

        duration = time.time() - start_time
        yield {
            "type": "command.completed",
            "command": "/diff",
            "mission_id": mission_id,
            "duration": duration,
            "payload": {"added": added, "removed": removed},
        }
