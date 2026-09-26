"""
Bounded Auto-Debugger
=====================
Manages self-healing feedback loops for failed verification gates.
Guarantees a hard bound of max_attempts (default 3). If repairs fail to pass all gates
within 3 attempts, performs an automated rollback to protect repo integrity.
"""

import os
import subprocess
from typing import Any

from app.core.logging_config import get_logger
from app.modules.agent.verification.schema import GateResult

logger = get_logger(__name__)


class AutoDebugSession:
    """Tracks state and attempts for an active self-healing session."""

    def __init__(self, task_id: str, workspace_root: str, max_attempts: int = 3):
        self.task_id = task_id
        self.workspace_root = os.path.abspath(workspace_root)
        self.max_attempts = max_attempts
        self.attempt_count = 0
        self.history: list[dict[str, Any]] = []
        self.is_resolved = False
        self.is_rolled_back = False

    def can_retry(self) -> bool:
        """True if current attempts are strictly less than max_attempts."""
        return self.attempt_count < self.max_attempts

    def record_attempt(self, failed_gate: GateResult, proposed_patch: str) -> int:
        """Increments attempt count and records diagnostic data."""
        self.attempt_count += 1
        self.history.append(
            {
                "attempt": self.attempt_count,
                "gate_name": failed_gate.gate_name,
                "error": failed_gate.message,
                "details": failed_gate.error_details,
                "proposed_patch": proposed_patch,
            }
        )
        logger.warning(
            f"Auto-debug attempt {self.attempt_count}/{self.max_attempts} for gate: {failed_gate.gate_name}"
        )
        return self.attempt_count

    def trigger_rollback(self, modified_files: list[str] | None = None) -> bool:
        """
        Restores modified files to their previous Git state.
        Ensures failed missions leave ZERO corrupted files in the repository.
        """
        logger.error(
            f"Max auto-fix attempts ({self.max_attempts}) reached for task {self.task_id}. Initiating automatic rollback."
        )
        self.is_rolled_back = True
        try:
            if modified_files:
                for f in modified_files:
                    subprocess.run(
                        f"git checkout -- {f}",
                        shell=True,
                        cwd=self.workspace_root,
                        capture_output=True,
                        check=False,
                    )
            else:
                subprocess.run(
                    "git stash push -m 'nemotron_auto_debug_rollback'",
                    shell=True,
                    cwd=self.workspace_root,
                    capture_output=True,
                    check=False,
                )
            return True
        except (subprocess.SubprocessError, OSError) as e:
            logger.error(f"Rollback command encountered exception: {e}")
            return False


class BoundedAutoDebugger:
    """Engine orchestrating bounded auto-debugging loops."""

    def __init__(self, workspace_root: str, max_attempts: int = 3):
        self.workspace_root = workspace_root
        self.max_attempts = max_attempts

    def create_session(self, task_id: str) -> AutoDebugSession:
        return AutoDebugSession(task_id, self.workspace_root, self.max_attempts)
