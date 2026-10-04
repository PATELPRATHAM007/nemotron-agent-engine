"""
Test Command Handler (/test)
============================
Detects project test frameworks (pytest, npm test/vitest, cargo, etc.)
and executes tests with structured failure analysis and debugging recommendations.
"""

import time
import os
from typing import Any, AsyncGenerator

from app.core.logging_config import get_logger
from app.modules.agent.commands.models import ParsedCommand
from app.modules.agent.tools.process_runner import process_runner

logger = get_logger(__name__)


class TestCommandHandler:
    """Orchestrates test execution across detected project frameworks."""

    @classmethod
    async def execute(
        cls,
        parsed: ParsedCommand,
        workspace_root: str,
        mission_id: str = "",
    ) -> AsyncGenerator[dict[str, Any], None]:
        start_time = time.time()
        subsystem = (parsed.args[0] if parsed.args else "").lower()

        yield {
            "type": "command.started",
            "command": "/test",
            "mission_id": mission_id,
            "timestamp": start_time,
            "payload": {"subsystem": subsystem},
        }

        # 1. Determine target test command
        cmd, cwd = cls._resolve_test_command(workspace_root, subsystem)

        yield {
            "type": "token",
            "content": f"🧪 **Running Tests**: `{cmd}` (cwd: `{os.path.basename(cwd)}`)\n\n",
        }
        yield {
            "type": "command.tool_started",
            "command": "/test",
            "tool": "process_runner",
            "payload": {"command": cmd, "cwd": cwd},
        }

        # 2. Execute tests
        result = await process_runner.run(cmd, cwd=cwd, timeout=120)

        yield {
            "type": "command.tool_completed",
            "command": "/test",
            "tool": "process_runner",
            "payload": {
                "exit_code": result.exit_code,
                "duration_seconds": result.duration_ms / 1000.0,
            },
        }

        # Output preview
        output = (result.stdout + "\n" + result.stderr).strip()
        lines = output.splitlines()
        preview = "\n".join(lines[-25:]) if len(lines) > 25 else output

        if result.exit_code == 0:
            yield {
                "type": "token",
                "content": f"```text\n{preview}\n```\n\n"
                           f"✅ **All Tests Passed Successfully** in {result.duration_seconds:.2f}s.\n",
            }
            yield {
                "type": "command.completed",
                "command": "/test",
                "mission_id": mission_id,
                "duration": time.time() - start_time,
                "payload": {"status": "passed", "exit_code": 0},
            }
        else:
            yield {
                "type": "token",
                "content": f"```text\n{preview}\n```\n\n"
                           f"❌ **Test Suite Failed** (Exit Code {result.exit_code}) in {result.duration_seconds:.2f}s.\n\n"
                           f"💡 **Suggested Next Step**: Run `/debug` with the failing test output to diagnose and fix the root cause.\n",
            }
            yield {
                "type": "command.failed",
                "command": "/test",
                "mission_id": mission_id,
                "duration": time.time() - start_time,
                "payload": {
                    "reason": f"Test runner exited with code {result.exit_code}",
                    "details": preview,
                    "suggested_next_step": "/debug failing tests",
                },
            }

    @classmethod
    def _resolve_test_command(cls, root: str, target: str) -> tuple[str, str]:
        # Check if user explicitly asked for frontend
        if target in ("frontend", "ui", "web"):
            frontend_dir = os.path.join(root, "frontend")
            if not os.path.isdir(frontend_dir):
                sibling_frontend = os.path.abspath(os.path.join(root, "..", "nemotron-agent-frontend"))
                if os.path.isdir(sibling_frontend):
                    return "npm test -- --run", sibling_frontend
            return "npm test -- --run", frontend_dir if os.path.isdir(frontend_dir) else root

        # Check Python pytest
        venv_pytest = os.path.join(root, ".venv", "bin", "pytest")
        pytest_cmd = venv_pytest if os.path.isfile(venv_pytest) else "pytest"

        if target and target not in ("backend", "all", "unit", "integration"):
            # Target is a specific file, directory, or pattern
            if target.endswith(".py") or "/" in target or "\\" in target:
                return f"{pytest_cmd} {target} -q", root
            return f"{pytest_cmd} -k '{target}' -q", root
        
        # Check if tests directory exists
        if os.path.isdir(os.path.join(root, "tests")):
            return f"{pytest_cmd} tests/ -q", root

        # Check Node package.json
        if os.path.isfile(os.path.join(root, "package.json")):
            return "npm test -- --run", root

        # Fallback to pytest
        return f"{pytest_cmd} -q", root
