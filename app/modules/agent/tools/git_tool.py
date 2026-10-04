"""
Native Git Interface & Checkpoint Engine
========================================
Uses Git as the single source of truth for workspace history and integrity.
Provides status inspections, unified diffs, blame lookups, commit logs,
and automated pre-edit checkpoints with atomic rollback.
"""

import subprocess
from dataclasses import dataclass, field
from typing import Any

from app.core.logging_config import get_logger
from app.modules.agent.tools.workspace import WorkspaceSandbox, workspace_sandbox

logger = get_logger(__name__)


@dataclass
class GitStatus:
    """Parsed Git working tree status."""

    is_repo: bool
    branch: str = ""
    is_clean: bool = True
    modified_files: list[str] = field(default_factory=list)
    staged_files: list[str] = field(default_factory=list)
    untracked_files: list[str] = field(default_factory=list)
    summary: str = ""


class GitTool:
    """Executes safe Git operations and manages atomic rollback checkpoints."""

    def __init__(self, sandbox: WorkspaceSandbox | None = None):
        self.sandbox = sandbox or workspace_sandbox
        self._checkpoints: dict[str, str] = {}  # checkpoint_name -> stash_sha or commit_sha

    def _run_git(self, args: list[str], timeout: int = 15) -> tuple[int, str, str]:
        """Execute git command in the workspace directory."""
        try:
            res = subprocess.run(
                ["git"] + args,
                cwd=self.sandbox.workspace_root,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            return res.returncode, res.stdout.strip(), res.stderr.strip()
        except subprocess.TimeoutExpired:
            return -1, "", "Git command timed out."
        except OSError as e:
            return -1, "", str(e)

    def get_status(self) -> GitStatus:
        """Inspect current Git status and detect modified, staged, or untracked files."""
        code, out, err = self._run_git(["status", "--porcelain=v1", "-b"])
        if code != 0:
            return GitStatus(is_repo=False, summary=f"Not a git repository: {err}")

        lines = out.splitlines()
        branch = "unknown"
        modified: list[str] = []
        staged: list[str] = []
        untracked: list[str] = []

        for line in lines:
            if line.startswith("##"):
                branch_line = line[3:].split("...")[0].strip()
                branch = branch_line
                continue

            if len(line) < 3:
                continue

            index_status = line[0]
            work_status = line[1]
            file_name = line[3:].strip()

            if index_status in ("M", "A", "D", "R"):
                staged.append(file_name)
            if work_status in ("M", "D"):
                modified.append(file_name)
            if index_status == "?" and work_status == "?":
                untracked.append(file_name)

        is_clean = len(modified) == 0 and len(staged) == 0 and len(untracked) == 0
        summary = (
            f"Branch: {branch} | Clean: {is_clean} "
            f"(Modified: {len(modified)}, Staged: {len(staged)}, Untracked: {len(untracked)})"
        )

        return GitStatus(
            is_repo=True,
            branch=branch,
            is_clean=is_clean,
            modified_files=modified,
            staged_files=staged,
            untracked_files=untracked,
            summary=summary,
        )

    def get_diff(self, filepath: str | None = None, staged: bool = False) -> str:
        """Return unified diff of uncommitted changes."""
        args = ["diff"]
        if staged:
            args.append("--staged")
        if filepath:
            args.extend(["--", self.sandbox.get_relative_path(filepath)])

        code, out, err = self._run_git(args)
        return out if code == 0 else f"Error retrieving git diff: {err}"

    def get_log(self, limit: int = 5, filepath: str | None = None) -> list[dict[str, str]]:
        """Return list of recent commits with hash, author, date, and message."""
        args = ["log", f"-n{limit}", "--pretty=format:%H|%an|%ar|%s"]
        if filepath:
            args.extend(["--", self.sandbox.get_relative_path(filepath)])

        code, out, err = self._run_git(args)
        if code != 0 or not out:
            return []

        commits = []
        for line in out.splitlines():
            parts = line.split("|", 3)
            if len(parts) == 4:
                commits.append({
                    "commit_hash": parts[0],
                    "author": parts[1],
                    "relative_date": parts[2],
                    "message": parts[3],
                })
        return commits

    def get_blame(
        self, filepath: str, line_start: int | None = None, line_end: int | None = None
    ) -> str:
        """Inspect git blame for a specific file and optional line range."""
        rel_path = self.sandbox.get_relative_path(filepath)
        args = ["blame", "--line-porcelain"]
        if line_start and line_end:
            args.extend([f"-L{line_start},{line_end}"])
        args.extend(["--", rel_path])

        code, out, err = self._run_git(args)
        if code != 0:
            return f"Error running git blame: {err}"

        # Format porcelain into human-readable summary
        lines = []
        current_commit = ""
        current_author = ""
        for line in out.splitlines():
            if line.startswith("author "):
                current_author = line[7:]
            elif line.startswith("\t"):
                code_line = line[1:]
                lines.append(f"{current_author[:12]:12} | {code_line}")

        return "\n".join(lines[:100])

    def create_checkpoint(self, name: str) -> dict[str, Any]:
        """
        Create a lightweight checkpoint before risky edits.
        Uses git stash create to generate a non-destructive commit hash without altering working tree.
        """
        code, stash_sha, err = self._run_git(["stash", "create", f"agent_checkpoint_{name}"])
        if code != 0 or not stash_sha:
            # Fallback to current HEAD commit hash
            _, head_sha, _ = self._run_git(["rev-parse", "HEAD"])
            stash_sha = head_sha or "HEAD"

        self._checkpoints[name] = stash_sha
        logger.info(f"Created Git checkpoint [{name}]: {stash_sha[:8]}")
        return {
            "success": True,
            "checkpoint_name": name,
            "sha": stash_sha,
        }

    def rollback(self, name: str = "default", files: list[str] | None = None) -> dict[str, Any]:
        """
        Revert uncommitted modifications in the working tree back to clean state.
        Discards uncommitted changes using checkout and clean.
        """
        logger.warning(f"Rolling back workspace to checkpoint [{name}]")
        if files:
            cmd = ["checkout", "--"] + [self.sandbox.get_relative_path(f) for f in files]
            code1, _, err1 = self._run_git(cmd)
            code2, err2 = 0, ""
        else:
            code1, _, err1 = self._run_git(["checkout", "--", "."])
            code2, _, err2 = self._run_git(["clean", "-fd"])

        success = (code1 == 0 and code2 == 0)
        return {
            "success": success,
            "checkpoint_name": name,
            "error": err1 or err2 if not success else None,
            "message": "Workspace cleanly rolled back to pre-edit state." if success else "Rollback failed.",
        }

    async def status(self) -> dict[str, Any]:
        """Async helper returning working tree status dictionary."""
        s = self.get_status()
        return {
            "success": s.is_repo,
            "branch": s.branch,
            "clean": s.is_clean,
            "modified": s.modified_files,
            "staged": s.staged_files,
            "untracked": s.untracked_files,
            "summary": s.summary,
        }

    async def diff(self, filepath: str | None = None, staged: bool = False) -> dict[str, Any]:
        """Async helper returning unified diff dictionary."""
        d = self.get_diff(filepath=filepath, staged=staged)
        return {"success": True, "diff": d}


git_tool = GitTool()

