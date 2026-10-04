"""
Mission Slash Commands & Terminal Shortcut Parser
=================================================
Bridges legacy SlashCommandParser to the first-class CommandParser and CommandRegistry.
"""

from typing import Any
from app.modules.agent.commands.parser import CommandParser
from app.modules.agent.commands.registry import command_registry


class SlashCommandParser:
    """Detects and parses slash commands and terminal shortcuts."""

    SUPPORTED_COMMANDS = {
        cmd.command for cmd in command_registry.list_commands()
    } | {
        "/approve", "/reject", "/pause", "/resume", "/stop", "/logs", "/context", "/rollback", "/permissions"
    }

    @classmethod
    def is_directive(cls, text: str) -> bool:
        trimmed = text.strip()
        if trimmed.startswith("!"):
            return True
        first_token = trimmed.split()[0].lower() if trimmed else ""
        return first_token in cls.SUPPORTED_COMMANDS or first_token.startswith("/")

    @classmethod
    def parse(cls, text: str) -> dict[str, Any]:
        """
        Parse command into a structured execution directive.
        """
        parsed = CommandParser.parse(text)
        if parsed.is_command:
            return {
                "is_directive": True,
                "type": "terminal_shortcut" if parsed.command == "!" else "slash_command",
                "command": parsed.command,
                "args": parsed.query_string,
                "parsed": parsed,
            }

        return {
            "is_directive": False,
            "type": "natural_language",
            "command": "",
            "args": text.strip(),
            "parsed": parsed,
        }
