"""
Mission Slash Commands & Terminal Shortcut Parser
=================================================
Parses user input for mission control directives:
  /plan, /status, /permissions, /approve, /reject, /pause, /resume,
  /stop, /diff, /test, /logs, /rollback, !<command>
"""

from typing import Any


class SlashCommandParser:
    """Detects and parses slash commands and terminal shortcuts."""

    SUPPORTED_COMMANDS = {
        "/plan",
        "/status",
        "/permissions",
        "/approve",
        "/reject",
        "/pause",
        "/resume",
        "/stop",
        "/diff",
        "/test",
        "/logs",
        "/context",
        "/rollback",
    }

    @classmethod
    def is_directive(cls, text: str) -> bool:
        trimmed = text.strip()
        if trimmed.startswith("!"):
            return True
        first_token = trimmed.split()[0].lower() if trimmed else ""
        return first_token in cls.SUPPORTED_COMMANDS

    @classmethod
    def parse(cls, text: str) -> dict[str, Any]:
        """
        Parse command into a structured execution directive.
        Returns:
          is_directive: bool
          command: str e.g. "/plan" or "!"
          args: str e.g. "git status"
        """
        trimmed = text.strip()
        if trimmed.startswith("!"):
            return {
                "is_directive": True,
                "type": "terminal_shortcut",
                "command": "!",
                "args": trimmed[1:].strip(),
            }

        parts = trimmed.split(maxsplit=1)
        cmd = parts[0].lower() if parts else ""
        args = parts[1].strip() if len(parts) > 1 else ""

        if cmd in cls.SUPPORTED_COMMANDS:
            return {
                "is_directive": True,
                "type": "slash_command",
                "command": cmd,
                "args": args,
            }

        return {
            "is_directive": False,
            "type": "natural_language",
            "command": "",
            "args": trimmed,
        }
