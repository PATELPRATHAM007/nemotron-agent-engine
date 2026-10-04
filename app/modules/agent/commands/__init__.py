"""
Agent Command System
====================
Provides first-class slash commands (/init, /plan, /review, /test, /debug, /fix, /explain,
/search, /inspect, /status, /diff, /commit, /undo, /reset, /clear, /help).
"""

from app.modules.agent.commands.models import (
    CommandDefinition,
    CommandRisk,
    ExecutionMode,
    ParsedCommand,
    CommandEvent,
)
from app.modules.agent.commands.parser import CommandParser
from app.modules.agent.commands.registry import CommandRegistry, command_registry

__all__ = [
    "CommandDefinition",
    "CommandRisk",
    "ExecutionMode",
    "ParsedCommand",
    "CommandEvent",
    "CommandParser",
    "CommandRegistry",
    "command_registry",
]
