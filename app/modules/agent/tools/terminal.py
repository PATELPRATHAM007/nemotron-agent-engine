"""
Sandboxed Terminal Execution Tool for Nemotron 3 Ultra Agents
"""

import asyncio
import os
from typing import Any


class TerminalTool:
    """Executes shell commands in a safe subprocess with timeouts and output capture."""

    def __init__(self, default_cwd: str = "/tmp"):
        self.default_cwd = default_cwd

    async def execute(
        self, command: str, cwd: str | None = None, timeout: int = 30
    ) -> dict[str, Any]:
        target_dir = cwd or self.default_cwd
        os.makedirs(target_dir, exist_ok=True)

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                cwd=target_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout
                )
                stdout = stdout_bytes.decode("utf-8", "replace")
                stderr = stderr_bytes.decode("utf-8", "replace")
                exit_code = proc.returncode

                # Truncate if output exceeds 8000 chars to protect context window
                if len(stdout) > 8000:
                    stdout = (
                        stdout[:8000] + "\n...[Output truncated to 8,000 characters]..."
                    )
                if len(stderr) > 4000:
                    stderr = stderr[:4000] + "\n...[Stderr truncated]..."

                return {
                    "success": exit_code == 0,
                    "exit_code": exit_code,
                    "stdout": stdout,
                    "stderr": stderr,
                }
            except asyncio.TimeoutError:
                try:
                    proc.kill()
                except ProcessLookupError:
                    pass
                return {
                    "success": False,
                    "exit_code": -1,
                    "stdout": "",
                    "stderr": f"Command timed out after {timeout} seconds.",
                }

        except OSError as e:
            return {
                "success": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Execution error: {e!s}",
            }


terminal_tool = TerminalTool()
