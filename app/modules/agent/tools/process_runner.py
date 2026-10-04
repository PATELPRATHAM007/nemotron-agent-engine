"""
Hardened Subprocess Runner & Background Task Manager
===================================================
Executes shell commands strictly confined within workspace boundaries with
timeout enforcement, output truncation protection, process group termination,
and background task lifecycle tracking (start, poll, kill).
"""

import asyncio
from dataclasses import dataclass, field
import datetime
import os
import signal
import uuid
from typing import Any

from app.core.logging_config import get_logger
from app.modules.agent.tools.workspace import WorkspaceSandbox, workspace_sandbox

logger = get_logger(__name__)

MAX_STDOUT_BYTES = 32 * 1024  # 32 KB max stdout to protect LLM context
MAX_STDERR_BYTES = 16 * 1024  # 16 KB max stderr


@dataclass
class ExecutionResult:
    """Structured result of a completed or timed-out process execution."""

    success: bool
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    command: str
    timed_out: bool = False
    truncated: bool = False


@dataclass
class BackgroundTask:
    """State of an ongoing background process."""

    task_id: str
    command: str
    process: asyncio.subprocess.Process
    started_at: str = field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    )
    stdout_buffer: list[str] = field(default_factory=list)
    stderr_buffer: list[str] = field(default_factory=list)


class ProcessRunner:
    """Sandboxed process execution engine and background job manager."""

    def __init__(self, sandbox: WorkspaceSandbox | None = None):
        self.sandbox = sandbox or workspace_sandbox
        self._background_tasks: dict[str, BackgroundTask] = {}

    async def run(
        self,
        command: str,
        cwd: str | None = None,
        timeout: int = 30,
        env_vars: dict[str, str] | None = None,
    ) -> ExecutionResult:
        """
        Execute shell command synchronously with timeout and output capture.
        Guarantees cwd is confined inside the workspace sandbox.
        """
        target_dir = self.sandbox.resolve_path(cwd or ".")
        effective_timeout = max(1, min(timeout, 300))
        start_time = asyncio.get_event_loop().time()

        # Build clean environment
        env = os.environ.copy()
        if env_vars:
            env.update(env_vars)

        try:
            # Start process in a new process group for clean subtree termination
            proc = await asyncio.create_subprocess_shell(
                command,
                cwd=target_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                preexec_fn=os.setsid if hasattr(os, "setsid") else None,
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(), timeout=effective_timeout
                )
                duration_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)

                stdout_text = stdout_bytes.decode("utf-8", errors="replace")
                stderr_text = stderr_bytes.decode("utf-8", errors="replace")
                truncated = False

                if len(stdout_text) > MAX_STDOUT_BYTES:
                    stdout_text = (
                        stdout_text[:MAX_STDOUT_BYTES]
                        + f"\n... [Stdout truncated to {MAX_STDOUT_BYTES // 1024} KB] ..."
                    )
                    truncated = True

                if len(stderr_text) > MAX_STDERR_BYTES:
                    stderr_text = (
                        stderr_text[:MAX_STDERR_BYTES]
                        + f"\n... [Stderr truncated to {MAX_STDERR_BYTES // 1024} KB] ..."
                    )
                    truncated = True

                return ExecutionResult(
                    success=(proc.returncode == 0),
                    exit_code=proc.returncode if proc.returncode is not None else 1,
                    stdout=stdout_text,
                    stderr=stderr_text,
                    duration_ms=duration_ms,
                    command=command,
                    timed_out=False,
                    truncated=truncated,
                )

            except asyncio.TimeoutError:
                # Terminate entire process group
                self._kill_process_tree(proc)
                duration_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)

                return ExecutionResult(
                    success=False,
                    exit_code=-1,
                    stdout="",
                    stderr=f"Command timed out after {effective_timeout} seconds. Process tree terminated.",
                    duration_ms=duration_ms,
                    command=command,
                    timed_out=True,
                )

        except OSError as e:
            return ExecutionResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr=f"Subprocess spawn error: {e!s}",
                duration_ms=0,
                command=command,
            )

    async def start_background(self, command: str, cwd: str | None = None) -> str:
        """Start a long-running process in the background and return task_id."""
        target_dir = self.sandbox.resolve_path(cwd or ".")
        task_id = f"bg_{uuid.uuid4().hex[:8]}"

        proc = await asyncio.create_subprocess_shell(
            command,
            cwd=target_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            preexec_fn=os.setsid if hasattr(os, "setsid") else None,
        )

        self._background_tasks[task_id] = BackgroundTask(
            task_id=task_id,
            command=command,
            process=proc,
        )
        logger.info(f"Started background process [{task_id}]: {command}")
        return task_id

    def get_background_status(self, task_id: str) -> dict[str, Any]:
        """Poll the status of a background process."""
        bg = self._background_tasks.get(task_id)
        if not bg:
            return {"error": f"Background task '{task_id}' not found."}

        is_running = bg.process.returncode is None
        return {
            "task_id": task_id,
            "command": bg.command,
            "is_running": is_running,
            "exit_code": bg.process.returncode,
            "started_at": bg.started_at,
        }

    def kill_background(self, task_id: str) -> bool:
        """Terminate a background process."""
        bg = self._background_tasks.get(task_id)
        if not bg:
            return False

        self._kill_process_tree(bg.process)
        del self._background_tasks[task_id]
        return True

    def _kill_process_tree(self, proc: asyncio.subprocess.Process) -> None:
        """Safely kill process and any child processes spawned."""
        try:
            if hasattr(os, "killpg") and proc.pid:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            else:
                proc.kill()
        except (ProcessLookupError, OSError):
            pass


process_runner = ProcessRunner()
