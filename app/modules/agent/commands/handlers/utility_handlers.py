"""
Utility Command Handlers (/clear, /help)
========================================
Manages chat session lifecycle clearing (preserving project memory)
and interactive command help discovery.
"""

import time
from typing import Any, AsyncGenerator

from app.core.logging_config import get_logger
from app.modules.agent.commands.models import ParsedCommand
from app.modules.missions.repository import mission_repository

logger = get_logger(__name__)


class UtilityCommandHandlers:
    """Handlers for /clear and /help commands."""

    @classmethod
    async def handle_clear(
        cls,
        parsed: ParsedCommand,
        workspace_root: str,
        mission_id: str = "",
    ) -> AsyncGenerator[dict[str, Any], None]:
        start_time = time.time()

        yield {
            "type": "command.started",
            "command": "/clear",
            "mission_id": mission_id,
            "timestamp": start_time,
        }

        # Clear ephemeral session messages from timeline if mission_id is active
        cleared_count = 0
        if mission_id and hasattr(mission_repository, "clear_mission_messages"):
            cleared_count = mission_repository.clear_mission_messages(mission_id)

        yield {
            "type": "token",
            "content": "🧹 **Session context cleared.**\n\n"
                       "✓ Ephemeral conversation history reset.\n"
                       "✓ Persistent project memory (`PROJECT.md` & indexed graph) preserved.\n",
        }

        duration = time.time() - start_time
        yield {
            "type": "command.completed",
            "command": "/clear",
            "mission_id": mission_id,
            "duration": duration,
            "payload": {"cleared_messages": cleared_count},
        }

    registry_provider: Any = None

    @classmethod
    async def handle_help(
        cls,
        parsed: ParsedCommand,
        workspace_root: str,
        mission_id: str = "",
    ) -> AsyncGenerator[dict[str, Any], None]:
        start_time = time.time()
        subcommand = (parsed.args[0] if parsed.args else "").lower()
        if subcommand.startswith("/"):
            subcommand = subcommand[1:]

        yield {
            "type": "command.started",
            "command": "/help",
            "mission_id": mission_id,
            "timestamp": start_time,
            "payload": {"subcommand": subcommand},
        }

        reg = cls.registry_provider() if callable(cls.registry_provider) else cls.registry_provider

        if subcommand:
            # Specific command help
            definition = reg.get("/" + subcommand) if reg else None
            if definition:
                examples_md = "\n".join([f"  - `{ex}`" for ex in definition.examples]) or "  - None"
                content = (
                    f"### Command Help: `{definition.command}`\n\n"
                    f"**Description**: {definition.description}\n\n"
                    f"- **Syntax**: `{definition.syntax}`\n"
                    f"- **Arguments**: {definition.arguments_description or 'None'}\n"
                    f"- **Risk Level**: `{definition.risk_level.value}` (Permission Tier: L{definition.permission_level})\n"
                    f"- **Requires Approval**: {'Yes' if definition.supports_approval else 'No'}\n\n"
                    f"**Examples**:\n{examples_md}\n"
                )
            else:
                content = f"❌ Unknown command `/{subcommand}`. Type `/help` to see all available commands.\n"
        else:
            # Full commands table
            commands = reg.list_commands() if reg else []
            
            by_risk: dict[str, list] = {"LOW": [], "MEDIUM": [], "HIGH": [], "SPECIAL": []}
            for cmd in commands:
                by_risk[cmd.risk_level.value].append(cmd)

            rows = []
            for r in ["SPECIAL", "LOW", "MEDIUM", "HIGH"]:
                for c in by_risk.get(r, []):
                    approval = "⚠️ Yes" if c.supports_approval else "No"
                    rows.append(f"| `{c.command}` | {c.description} | `{c.syntax}` | `{c.risk_level.value}` | {approval} |")

            table_md = "\n".join(rows)

            content = (
                f"### Nemotron Agent Engine: Available Commands\n\n"
                f"Type any command directly in the chat or terminal. For detailed usage, run `/help <command>`.\n\n"
                f"| Command | Description | Syntax | Risk | Approval |\n"
                f"| :--- | :--- | :--- | :--- | :--- |\n"
                f"{table_md}\n\n"
                f"💡 *Tip: You can also use `!<command>` for direct sandboxed shell execution (e.g. `!git status`).*\n"
            )

        yield {
            "type": "token",
            "content": content,
        }

        duration = time.time() - start_time
        yield {
            "type": "command.completed",
            "command": "/help",
            "mission_id": mission_id,
            "duration": duration,
        }
