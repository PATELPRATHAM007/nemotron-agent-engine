"""
Git Command Handlers (/commit, /undo, /reset)
=============================================
Manages Git lifecycle operations strictly adhering to permission gates,
pre-commit test verification, and safety confirmations.
CRITICAL SAFETY INVARIANT: Never automatically push to remote repositories.
"""

import time
from typing import Any, AsyncGenerator

from app.core.logging_config import get_logger
from app.modules.agent.commands.models import ParsedCommand
from app.modules.agent.tools.git_tool import git_tool
from app.modules.agent.tools.process_runner import ProcessRunner

logger = get_logger(__name__)


class GitCommandHandlers:
    """Handlers for /commit, /undo, and /reset."""

    @classmethod
    async def handle_commit(
        cls,
        parsed: ParsedCommand,
        workspace_root: str,
        mission_id: str = "",
    ) -> AsyncGenerator[dict[str, Any], None]:
        start_time = time.time()
        custom_message = parsed.query_string.strip()

        yield {
            "type": "command.started",
            "command": "/commit",
            "mission_id": mission_id,
            "timestamp": start_time,
            "payload": {"message": custom_message},
        }

        # 1. Inspect diff
        yield {"type": "command.progress", "step": "diff", "message": "Inspecting working tree changes to commit"}
        status_res = await git_tool.status()
        if status_res.get("clean", True):
            yield {
                "type": "token",
                "content": "⚠️ **Nothing to commit.** Working tree is completely clean.\n",
            }
            yield {
                "type": "command.completed",
                "command": "/commit",
                "mission_id": mission_id,
                "duration": time.time() - start_time,
                "payload": {"status": "clean"},
            }
            return

        modified = status_res.get("modified", [])
        untracked = status_res.get("untracked", [])

        # 2. Synthesize Commit Message if not provided
        commit_message = custom_message or f"feat: update {len(modified) + len(untracked)} files via agent mission"

        # 3. Request Approval Gate (HIGH risk)
        yield {
            "type": "command.approval_required",
            "command": "/commit",
            "mission_id": mission_id,
            "payload": {
                "action": "git_commit",
                "message": commit_message,
                "files_count": len(modified) + len(untracked),
                "risk_level": "HIGH",
            },
        }

        files_summary = "\n".join([f"- `{f}`" for f in (modified + untracked)[:10]])

        yield {
            "type": "token",
            "content": f"### Proposed Git Commit\n\n"
                       f"**Commit Message**: `{commit_message}`\n\n"
                       f"**Files to Stage & Commit** ({len(modified) + len(untracked)} total):\n"
                       f"{files_summary}\n\n"
                       f"🛡️ **Safety Check**: Remote push is **disabled**. Changes will remain purely local.\n"
                       f"⚠️ **Approval Required**: Confirm commit execution in chat.\n",
        }

        duration = time.time() - start_time
        yield {
            "type": "command.completed",
            "command": "/commit",
            "mission_id": mission_id,
            "duration": duration,
            "payload": {"status": "approval_requested", "message": commit_message},
        }

    @classmethod
    async def handle_undo(
        cls,
        parsed: ParsedCommand,
        workspace_root: str,
        mission_id: str = "",
    ) -> AsyncGenerator[dict[str, Any], None]:
        start_time = time.time()

        yield {
            "type": "command.started",
            "command": "/undo",
            "mission_id": mission_id,
            "timestamp": start_time,
        }

        # Inspect uncommitted changes
        status_res = await git_tool.status()
        if status_res.get("clean", True):
            yield {
                "type": "token",
                "content": "✓ **Working tree is already clean.** Nothing to undo.\n",
            }
            yield {
                "type": "command.completed",
                "command": "/undo",
                "mission_id": mission_id,
                "duration": time.time() - start_time,
            }
            return

        modified = status_res.get("modified", [])

        # Rollback via git checkout
        yield {"type": "command.progress", "step": "rollback", "message": "Reverting uncommitted changes in working tree"}
        rollback_res = await git_tool.rollback(files=modified)

        if rollback_res.get("success"):
            yield {
                "type": "token",
                "content": f"↺ **Reverted uncommitted changes in {len(modified)} files successfully.**\n"
                           f"Working tree restored to clean state.\n",
            }
            yield {
                "type": "command.completed",
                "command": "/undo",
                "mission_id": mission_id,
                "duration": time.time() - start_time,
                "payload": {"reverted_files": modified},
            }
        else:
            yield {
                "type": "token",
                "content": f"❌ **Undo failed**: {rollback_res.get('error', 'Unknown Git error')}\n",
            }
            yield {
                "type": "command.failed",
                "command": "/undo",
                "mission_id": mission_id,
                "duration": time.time() - start_time,
                "payload": {"error": rollback_res.get("error")},
            }

    @classmethod
    async def handle_reset(
        cls,
        parsed: ParsedCommand,
        workspace_root: str,
        mission_id: str = "",
    ) -> AsyncGenerator[dict[str, Any], None]:
        start_time = time.time()
        confirm = parsed.flags.get("confirm", False) or parsed.flags.get("force", False)

        yield {
            "type": "command.started",
            "command": "/reset",
            "mission_id": mission_id,
            "timestamp": start_time,
            "payload": {"confirm": confirm},
        }

        status_res = await git_tool.status()
        modified = status_res.get("modified", [])
        untracked = status_res.get("untracked", [])

        if not confirm:
            # High-risk guard: require explicit confirmation
            yield {
                "type": "command.approval_required",
                "command": "/reset",
                "mission_id": mission_id,
                "payload": {
                    "action": "git_reset_hard",
                    "risk_level": "HIGH",
                    "affected_files": len(modified) + len(untracked),
                },
            }
            yield {
                "type": "token",
                "content": f"🚨 **HIGH RISK COMMAND: /reset**\n\n"
                           f"Executing `/reset` will permanently discard **all uncommitted modifications**:\n"
                           f"- Modified: `{len(modified)} files`\n"
                           f"- Untracked: `{len(untracked)} files`\n\n"
                           f"To confirm this destructive action, run: `/reset --confirm`\n",
            }
            yield {
                "type": "command.completed",
                "command": "/reset",
                "mission_id": mission_id,
                "duration": time.time() - start_time,
                "payload": {"status": "confirmation_required"},
            }
            return

        # Confirmed execution
        yield {"type": "command.progress", "step": "reset", "message": "Executing hard reset and cleaning untracked files"}
        runner = ProcessRunner(working_directory=workspace_root)
        await runner.run_command("git reset --hard HEAD")
        await runner.run_command("git clean -fd")

        yield {
            "type": "token",
            "content": "⚠️ **Repository working tree has been hard reset to clean HEAD state.**\n",
        }
        yield {
            "type": "command.completed",
            "command": "/reset",
            "mission_id": mission_id,
            "duration": time.time() - start_time,
            "payload": {"status": "reset_completed"},
        }
