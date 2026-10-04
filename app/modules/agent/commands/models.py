"""
Command System Data Models & Event Schemas
==========================================
Defines metadata, risk levels, execution modes, and event types for first-class agent commands.
"""

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class CommandRisk(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    SPECIAL = "SPECIAL"


class ExecutionMode(str, Enum):
    DIRECT = "direct"
    PLANNING = "planning"
    REACT = "react"
    VERIFICATION = "verification"


class CommandDefinition(BaseModel):
    """Declarative specification for an agent command."""
    command: str = Field(..., description="Canonical command string starting with '/', e.g. '/init'")
    description: str = Field(..., description="Concise human-readable explanation of command purpose")
    syntax: str = Field(..., description="Usage syntax, e.g. '/test [subsystem]'")
    arguments_description: str = Field("", description="Description of accepted arguments and flags")
    risk_level: CommandRisk = Field(default=CommandRisk.LOW, description="Operational risk level")
    permission_level: int = Field(default=0, ge=0, le=5, description="Required permission gate tier (0-5)")
    required_context: list[str] = Field(default_factory=list, description="Context layers needed (e.g. repo_map, git_diff)")
    required_tools: list[str] = Field(default_factory=list, description="Tools utilized during execution")
    execution_mode: ExecutionMode = Field(default=ExecutionMode.DIRECT, description="Execution pattern")
    supports_streaming: bool = Field(default=True, description="Whether execution streams progressive tokens/events")
    supports_approval: bool = Field(default=False, description="Whether command triggers interactive approval gates")
    supports_cancellation: bool = Field(default=True, description="Whether execution can be aborted safely")
    examples: list[str] = Field(default_factory=list, description="Usage examples for documentation and autocomplete")


class ParsedCommand(BaseModel):
    """Result of parsing user input into structured command directives."""
    raw_text: str
    is_command: bool = False
    command: str = ""
    subcommand: str | None = None
    args: list[str] = Field(default_factory=list)
    flags: dict[str, Any] = Field(default_factory=dict)
    query_string: str = ""
    error: str | None = None


class CommandEvent(BaseModel):
    """Structured event emitted during command lifecycle."""
    type: str = Field(..., description="Event type: command.started, command.progress, etc.")
    command: str
    mission_id: str = ""
    timestamp: float = 0.0
    payload: dict[str, Any] = Field(default_factory=dict)
