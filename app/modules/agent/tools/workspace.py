"""
Unified Workspace Sandbox & Concurrency Guard
=============================================
Enforces strict filesystem path boundaries within the workspace, prevents directory
traversal attacks, tracks file modification times and SHA-256 hashes, and detects
concurrency conflicts when files are edited externally during agent execution.
"""

import hashlib
import os
from typing import Any

from app.core.exceptions import ScopeViolationError
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class ConcurrencyConflictError(RuntimeError):
    """Raised when a file on disk has changed since the agent retrieved its context."""


class WorkspaceSandbox:
    """Confines filesystem operations to authorized repository boundaries."""

    def __init__(self, workspace_root: str = "."):
        self.workspace_root = os.path.abspath(workspace_root)
        # Tracks file fingerprints: relative_path -> {"sha256": str, "mtime": float}
        self._fingerprints: dict[str, dict[str, Any]] = {}

    def resolve_path(self, filepath: str) -> str:
        """
        Normalize and validate that target path stays strictly inside workspace boundaries.
        Raises PermissionError if path attempts directory traversal outside workspace.
        """
        clean_path = filepath.strip().strip("'\"")
        if os.path.isabs(clean_path):
            abs_path = os.path.abspath(clean_path)
        else:
            abs_path = os.path.abspath(os.path.join(self.workspace_root, clean_path))

        # Boundary check
        try:
            common = os.path.commonpath([self.workspace_root, abs_path])
        except ValueError as e:
            # Different drives on Windows or invalid paths
            raise PermissionError(f"Access denied: path '{filepath}' is outside workspace '{self.workspace_root}'") from e

        if common != self.workspace_root:
            raise PermissionError(f"Access denied: path '{filepath}' escapes workspace '{self.workspace_root}'")

        return abs_path

    def get_relative_path(self, filepath: str) -> str:
        """Return path relative to workspace root."""
        abs_path = self.resolve_path(filepath)
        return os.path.relpath(abs_path, self.workspace_root)

    def compute_fingerprint(self, filepath: str) -> dict[str, Any]:
        """Compute SHA-256 and modification time of a file on disk."""
        abs_path = self.resolve_path(filepath)
        if not os.path.exists(abs_path):
            return {"exists": False, "sha256": "", "mtime": 0.0, "size": 0}

        stat = os.stat(abs_path)
        hasher = hashlib.sha256()
        with open(abs_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)

        fp = {
            "exists": True,
            "sha256": hasher.hexdigest(),
            "mtime": stat.st_mtime,
            "size": stat.st_size,
        }
        rel_path = self.get_relative_path(abs_path)
        self._fingerprints[rel_path] = fp
        return fp

    def record_snapshot(self, filepath: str) -> str:
        """Record the baseline SHA-256 hash when reading a file."""
        fp = self.compute_fingerprint(filepath)
        return fp["sha256"]

    def verify_no_conflict(self, filepath: str, expected_base_sha256: str | None = None) -> None:
        """
        Verify that file on disk has not been modified since snapshot was recorded.
        Raises ConcurrencyConflictError if hashes do not match.
        """
        abs_path = self.resolve_path(filepath)
        if not os.path.exists(abs_path):
            # If expected hash is non-empty, file was deleted externally
            if expected_base_sha256:
                raise ConcurrencyConflictError(
                    f"Concurrency conflict: file '{filepath}' was deleted externally while agent was planning."
                )
            return

        current_fp = self.compute_fingerprint(filepath)
        rel_path = self.get_relative_path(abs_path)

        baseline_hash = expected_base_sha256 or self._fingerprints.get(rel_path, {}).get("sha256")
        if baseline_hash and current_fp["sha256"] != baseline_hash:
            raise ConcurrencyConflictError(
                f"Concurrency conflict: file '{filepath}' was modified externally (Disk: {current_fp['sha256'][:8]} != Baseline: {baseline_hash[:8]}). "
                "Agent must re-read the file before applying changes."
            )

    def read_text(self, filepath: str) -> str:
        """Read file contents safely and record its baseline fingerprint."""
        abs_path = self.resolve_path(filepath)
        if not os.path.exists(abs_path):
            raise FileNotFoundError(f"File not found: '{filepath}'")
        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        self.record_snapshot(filepath)
        return content

    def write_text(self, filepath: str, content: str, expected_base_sha256: str | None = None) -> int:
        """Write content safely with concurrency check and directory creation."""
        abs_path = self.resolve_path(filepath)
        self.verify_no_conflict(filepath, expected_base_sha256=expected_base_sha256)

        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)

        self.compute_fingerprint(filepath)
        return len(content.encode("utf-8"))


# Global default workspace sandbox pointing to current repository root
workspace_sandbox = WorkspaceSandbox()
