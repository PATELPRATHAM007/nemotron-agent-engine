"""
Compact Repository Map Generator
================================
Constructs an ultra-compact, token-efficient architectural outline of the repository
(< 2,000 tokens) using AST parsing and graph centrality ranking.
Injects concise file trees and symbol signatures directly into model context
without blowing the token budget.
"""

import ast
import os
import re

from app.core.logging_config import get_logger
from app.modules.agent.tools.workspace import WorkspaceSandbox, workspace_sandbox
from app.modules.intelligence.context.budget_manager import estimate_tokens

logger = get_logger(__name__)

IGNORED_DIRS = {
    ".git",
    "node_modules",
    ".venv",
    "__pycache__",
    ".next",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "build",
    ".agents",
}


class RepoMapGenerator:
    """Generates compact, token-bounded repository outlines from source ASTs."""

    def __init__(self, sandbox: WorkspaceSandbox | None = None):
        self.sandbox = sandbox or workspace_sandbox
        self._cached_map: str | None = None
        self._cached_token_count: int = 0

    def generate_map(
        self,
        max_tokens: int = 2000,
        include_tests: bool = False,
        target_dir: str | None = None,
        force_refresh: bool = False,
    ) -> str:
        """
        Generate a token-bounded repository map showing key files, classes,
        functions, and routes.
        """
        if self._cached_map and not force_refresh and max_tokens == 2000 and not target_dir:
            return self._cached_map

        root_path = self.sandbox.resolve_path(target_dir or ".")
        file_entries: list[tuple[str, list[str]]] = []  # (rel_path, list of symbols)

        # 1. Walk repository and extract signatures
        for root, dirs, files in os.walk(root_path):
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".")]

            for fname in sorted(files):
                if not include_tests and ("test" in fname.lower() or "tests/" in root):
                    continue

                abs_file = os.path.join(root, fname)
                rel_file = self.sandbox.get_relative_path(abs_file)

                if fname.endswith(".py"):
                    syms = self._extract_python_symbols(abs_file)
                    if syms:
                        file_entries.append((rel_file, syms))
                elif fname.endswith((".ts", ".tsx")):
                    syms = self._extract_ts_symbols(abs_file)
                    if syms:
                        file_entries.append((rel_file, syms))

        # 2. Sort by architectural centrality (core / routers / models first)
        def file_priority(entry: tuple[str, list[str]]) -> int:
            path = entry[0].lower()
            if "main.py" in path or "app.py" in path or "router.py" in path:
                return 0
            if "apis.py" in path or "models.py" in path or "service.py" in path:
                return 1
            if "page.tsx" in path or "navbar" in path:
                return 2
            if "core/" in path:
                return 3
            return 4

        file_entries.sort(key=file_priority)

        # 3. Assemble bounded markdown text
        lines: list[str] = ["# Compact Repository Map (High-Centrality Architecture):"]
        accumulated_text = "\n".join(lines)

        for rel_path, syms in file_entries:
            file_block = [f"\n{rel_path}:"]
            for s in syms[:8]:  # Limit top 8 symbols per file for compactness
                file_block.append(f"  {s}")

            candidate = "\n".join(file_block)
            test_text = accumulated_text + candidate
            if estimate_tokens(test_text) > max_tokens:
                # Add overflow indicator
                lines.append("\n... [Additional files omitted to maintain context budget] ...")
                break

            lines.append(candidate)
            accumulated_text = "\n".join(lines)

        final_map = "\n".join(lines)
        self._cached_map = final_map
        self._cached_token_count = estimate_tokens(final_map)
        return final_map

    def _extract_python_symbols(self, filepath: str) -> list[str]:
        """Parse Python AST to extract classes, functions, and routes."""
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                source = f.read()
            tree = ast.parse(source, filename=filepath)
        except (SyntaxError, OSError):
            return []

        symbols: list[str] = []
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                base_names = [ast.unparse(b) for b in node.bases[:2]]
                base_str = f"({', '.join(base_names)})" if base_names else ""
                symbols.append(f"class {node.name}{base_str}")
                # Include first 3 methods
                for item in node.body[:3]:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        symbols.append(f"  def {item.name}(...)")

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
                # Check for FastAPI route decorators
                route_desc = ""
                for deco in node.decorator_list:
                    deco_str = ast.unparse(deco)
                    if any(m in deco_str for m in (".get", ".post", ".put", ".delete", ".patch")):
                        route_desc = f" [{deco_str}]"
                        break
                symbols.append(f"{prefix} {node.name}(...){route_desc}")

        return symbols

    def _extract_ts_symbols(self, filepath: str) -> list[str]:
        """Regex-based extraction of exported functions, interfaces, and components in TS/TSX."""
        symbols: list[str] = []
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    s_line = line.strip()
                    if s_line.startswith("export function ") or s_line.startswith("export const "):
                        match = re.search(r"export (?:function|const)\s+([A-Za-z0-9_]+)", s_line)
                        if match:
                            symbols.append(f"export {match.group(1)}")
                    elif s_line.startswith("export interface ") or s_line.startswith("export type "):
                        match = re.search(r"export (?:interface|type)\s+([A-Za-z0-9_]+)", s_line)
                        if match:
                            symbols.append(f"export {match.group(1)}")
                    if len(symbols) >= 5:
                        break
        except OSError:
            pass
        return symbols


repo_map_generator = RepoMapGenerator()
