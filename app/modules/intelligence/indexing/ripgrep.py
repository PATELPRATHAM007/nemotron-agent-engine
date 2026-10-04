"""
Fast Ripgrep & Regex Search Tool
================================
High-performance code search engine utilizing native ripgrep (rg) with
a fast Python regex fallback. Supports file-type filtering, path boundaries,
case sensitivity, and bounded result sets to protect context token budgets.
"""

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Any

from app.core.logging_config import get_logger
from app.modules.agent.tools.workspace import WorkspaceSandbox, workspace_sandbox

logger = get_logger(__name__)


@dataclass
class SearchMatch:
    """Individual matching line found in a file."""

    filepath: str
    line_number: int
    line_content: str
    match_snippet: str = ""


@dataclass
class SearchResult:
    """Aggregated result of a ripgrep search operation."""

    success: bool
    query: str
    total_matches: int = 0
    matches: list[SearchMatch] = field(default_factory=list)
    engine_used: str = "ripgrep"  # "ripgrep" or "python_fallback"
    error: str | None = None
    truncated: bool = False


class RipgrepSearchEngine:
    """Executes high-speed exact and regex searches across repository source files."""

    def __init__(self, sandbox: WorkspaceSandbox | None = None):
        self.sandbox = sandbox or workspace_sandbox
        self.has_rg = shutil.which("rg") is not None

    def search(
        self,
        query: str,
        path_filter: str | None = None,
        file_types: list[str] | None = None,
        case_sensitive: bool = False,
        is_regex: bool = False,
        max_results: int = 50,
    ) -> SearchResult:
        """
        Execute search across the repository.
        Attempts native ripgrep first; falls back to Python regex if unavailable.
        """
        if not query.strip():
            return SearchResult(success=False, query=query, error="Search query cannot be empty.")

        target_dir = self.sandbox.resolve_path(path_filter or ".")

        if self.has_rg:
            try:
                return self._search_ripgrep(
                    query=query,
                    target_dir=target_dir,
                    file_types=file_types,
                    case_sensitive=case_sensitive,
                    is_regex=is_regex,
                    max_results=max_results,
                )
            except Exception as e:
                logger.warning(f"Ripgrep execution failed ({e}); falling back to Python search.")

        return self._search_python(
            query=query,
            target_dir=target_dir,
            file_types=file_types,
            case_sensitive=case_sensitive,
            is_regex=is_regex,
            max_results=max_results,
        )

    def _search_ripgrep(
        self,
        query: str,
        target_dir: str,
        file_types: list[str] | None,
        case_sensitive: bool,
        is_regex: bool,
        max_results: int,
    ) -> SearchResult:
        """Execute search using native ripgrep binary."""
        args = ["rg", "--json"]
        if not case_sensitive:
            args.append("-i")
        if not is_regex:
            args.append("-F")

        # Type globs
        if file_types:
            for ft in file_types:
                clean_ext = ft.lstrip(".")
                args.extend(["-g", f"*.{clean_ext}"])

        # Ignore standard noisy build dirs
        for ignore_dir in [".git", "node_modules", ".venv", "__pycache__", ".next", ".pytest_cache", ".ruff_cache"]:
            args.extend(["-g", f"!**/{ignore_dir}/**"])

        args.extend(["--", query, target_dir])

        proc = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )

        matches: list[SearchMatch] = []
        truncated = False

        for line in proc.stdout.splitlines():
            if len(matches) >= max_results:
                truncated = True
                break

            try:
                data = json.loads(line)
                if data.get("type") == "match":
                    payload = data.get("data", {})
                    path_data = payload.get("path", {})
                    raw_path = path_data.get("text", "")
                    rel_path = self.sandbox.get_relative_path(raw_path)
                    line_num = payload.get("line_number", 1)
                    line_text = payload.get("lines", {}).get("text", "").rstrip("\r\n")

                    matches.append(
                        SearchMatch(
                            filepath=rel_path,
                            line_number=line_num,
                            line_content=line_text[:300],  # Cap line width
                            match_snippet=line_text.strip(),
                        )
                    )
            except json.JSONDecodeError:
                continue

        return SearchResult(
            success=True,
            query=query,
            total_matches=len(matches),
            matches=matches,
            engine_used="ripgrep",
            truncated=truncated,
        )

    def _search_python(
        self,
        query: str,
        target_dir: str,
        file_types: list[str] | None,
        case_sensitive: bool,
        is_regex: bool,
        max_results: int,
    ) -> SearchResult:
        """High-speed pure-Python regex search fallback."""
        flags = 0 if case_sensitive else re.IGNORECASE
        pattern_str = query if is_regex else re.escape(query)
        try:
            compiled = re.compile(pattern_str, flags)
        except re.error as e:
            return SearchResult(success=False, query=query, error=f"Invalid regex: {e!s}")

        ignored_dirs = {".git", "node_modules", ".venv", "__pycache__", ".next", ".pytest_cache", ".ruff_cache"}
        allowed_extensions = {f".{ft.lstrip('.')}" for ft in file_types} if file_types else None

        matches: list[SearchMatch] = []
        truncated = False

        for root, dirs, files in os.walk(target_dir):
            dirs[:] = [d for d in dirs if d not in ignored_dirs and not d.startswith(".")]

            for fname in files:
                if len(matches) >= max_results:
                    truncated = True
                    break

                if allowed_extensions and not any(fname.endswith(ext) for ext in allowed_extensions):
                    continue

                abs_file = os.path.join(root, fname)
                try:
                    with open(abs_file, "r", encoding="utf-8", errors="ignore") as f:
                        for idx, line in enumerate(f, 1):
                            if compiled.search(line):
                                rel_path = self.sandbox.get_relative_path(abs_file)
                                matches.append(
                                    SearchMatch(
                                        filepath=rel_path,
                                        line_number=idx,
                                        line_content=line.rstrip("\r\n")[:300],
                                        match_snippet=line.strip(),
                                    )
                                )
                                if len(matches) >= max_results:
                                    truncated = True
                                    break
                except OSError:
                    continue

            if truncated:
                break

        return SearchResult(
            success=True,
            query=query,
            total_matches=len(matches),
            matches=matches,
            engine_used="python_fallback",
            truncated=truncated,
        )

    def search_text(
        self,
        query: str,
        workspace_root: str | None = None,
        max_results: int = 50,
    ) -> list[dict[str, Any]]:
        """Convenience method returning a list of match dictionaries."""
        res = self.search(query=query, max_results=max_results)
        return [
            {
                "filepath": m.filepath,
                "line_number": m.line_number,
                "line_text": m.line_content,
            }
            for m in res.matches
        ]


ripgrep_search = RipgrepSearchEngine()

