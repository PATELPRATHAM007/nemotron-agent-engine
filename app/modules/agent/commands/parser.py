"""
Robust Command Parser
=====================
Parses user input into structured commands, flags, quoted arguments, and directives
with support for unicode, multiline content, and terminal shortcuts (!<cmd>).
"""

import re
import shlex
from typing import Any
from app.modules.agent.commands.models import ParsedCommand


class CommandParser:
    """Parser for agent slash commands and shortcuts."""

    COMMAND_PATTERN = re.compile(r"^/([a-zA-Z0-9_\-]+)(?:\s+(.*))?$", re.DOTALL)

    @classmethod
    def parse(cls, text: str) -> ParsedCommand:
        """
        Parse raw user input into a structured ParsedCommand.
        
        Examples:
          /init --full
          /plan "implement OAuth authentication"
          /test backend --coverage
          /search "websocket connection"
          !git status
        """
        if not text or not text.strip():
            return ParsedCommand(raw_text=text or "", is_command=False)

        trimmed = text.strip()

        # Handle terminal shortcut prefix: !<command>
        if trimmed.startswith("!"):
            shortcut_cmd = trimmed[1:].strip()
            return ParsedCommand(
                raw_text=text,
                is_command=True,
                command="!",
                args=[shortcut_cmd] if shortcut_cmd else [],
                query_string=shortcut_cmd,
            )

        match = cls.COMMAND_PATTERN.match(trimmed)
        if not match:
            return ParsedCommand(
                raw_text=text,
                is_command=False,
                query_string=trimmed,
            )

        cmd_name = "/" + match.group(1).lower()
        tail = (match.group(2) or "").strip()

        args: list[str] = []
        flags: dict[str, Any] = {}

        if tail:
            # Tokenize arguments respecting quotes using shlex
            try:
                # Use POSIX mode with unicode preservation
                tokens = shlex.split(tail, posix=True)
            except ValueError:
                # If unmatched quotes occur, fallback to standard whitespace split without crashing
                tokens = tail.split()

            # Separate flags from positional arguments
            for token in tokens:
                if token.startswith("--"):
                    flag_body = token[2:]
                    if "=" in flag_body:
                        k, v = flag_body.split("=", 1)
                        flags[k] = v
                    else:
                        flags[flag_body] = True
                elif token.startswith("-") and len(token) > 1 and not token[1].isdigit():
                    # Short flags e.g. -v or -f
                    flag_body = token[1:]
                    for char in flag_body:
                        flags[char] = True
                else:
                    args.append(token)

        subcommand = args[0] if args else None

        return ParsedCommand(
            raw_text=text,
            is_command=True,
            command=cmd_name,
            subcommand=subcommand,
            args=args,
            flags=flags,
            query_string=tail,
        )
