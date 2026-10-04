"""
Git History & Blame Retriever
=============================
Provides historical commit context, recent file changes, and line-level blame
metadata to explain why past architectural decisions and bug fixes were made.
"""

from dataclasses import dataclass

from app.modules.agent.tools.git_tool import GitTool, git_tool
from app.modules.agent.tools.workspace import WorkspaceSandbox, workspace_sandbox


@dataclass
class CommitEntry:
    """Historical commit metadata."""

    commit_hash: str
    author: str
    relative_date: str
    message: str


class GitHistoryRetriever:
    """Retrieves targeted commit history and blame context for files and symbols."""

    def __init__(self, tool: GitTool | None = None, sandbox: WorkspaceSandbox | None = None):
        self.tool = tool or git_tool
        self.sandbox = sandbox or workspace_sandbox

    def get_recent_file_history(self, filepath: str, limit: int = 5) -> list[CommitEntry]:
        """Fetch the most recent commits touching a specific file."""
        logs = self.tool.get_log(limit=limit, filepath=filepath)
        return [CommitEntry(**entry) for entry in logs]

    def get_line_blame(
        self, filepath: str, line_start: int | None = None, line_end: int | None = None
    ) -> str:
        """Fetch human-readable blame information for a range of code lines."""
        return self.tool.get_blame(filepath=filepath, line_start=line_start, line_end=line_end)

    def search_commits(self, query: str, limit: int = 5) -> list[CommitEntry]:
        """Search commit messages across repository history for keywords or issues."""
        code, out, _ = self.tool._run_git(["log", f"-n{limit}", f"--grep={query}", "--pretty=format:%H|%an|%ar|%s"])
        if code != 0 or not out:
            return []

        commits = []
        for line in out.splitlines():
            parts = line.split("|", 3)
            if len(parts) == 4:
                commits.append(
                    CommitEntry(
                        commit_hash=parts[0],
                        author=parts[1],
                        relative_date=parts[2],
                        message=parts[3],
                    )
                )
        return commits


git_history_retriever = GitHistoryRetriever()
