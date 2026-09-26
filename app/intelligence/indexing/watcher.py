r"""
Incremental Repository File Watcher
===================================
Listens for filesystem modifications and applies $O(\Delta)$ incremental updates
to the code fingerprint catalog, symbol index, and repo knowledge graph.
Ignores whitespace and comment changes when AST structure is invariant.
"""

import os
from typing import Any

from app.core.logging_config import get_logger
from app.intelligence.indexing.fingerprint import CodeFingerprint, fingerprint_file
from app.intelligence.indexing.symbol_extractor import SymbolIndex

logger = get_logger(__name__)


class IncrementalFileWatcher:
    """Monitors repository files and performs incremental AST & graph synchronizations."""

    def __init__(self, workspace_root: str, symbol_index: SymbolIndex | None = None):
        self.workspace_root = os.path.abspath(workspace_root)
        self.symbol_index = symbol_index or SymbolIndex(self.workspace_root)
        self.fingerprints: dict[str, CodeFingerprint] = {}

    def handle_file_change(self, rel_path: str) -> dict[str, Any]:
        """
        Process a detected change for a single Python file.
        Returns diagnostic dictionary describing the action taken.
        """
        if not rel_path.endswith(".py"):
            return {"action": "skipped", "reason": "not_python"}

        full_path = os.path.join(self.workspace_root, rel_path)
        if not os.path.exists(full_path):
            # File was deleted
            self.fingerprints.pop(rel_path, None)
            return {"action": "deleted", "file": rel_path}

        old_fp = self.fingerprints.get(rel_path)
        new_fp = fingerprint_file(full_path)

        # 1. Byte-level exact match
        if old_fp and old_fp.file_hash == new_fp.file_hash:
            return {
                "action": "ignored",
                "reason": "identical_file_hash",
                "file": rel_path,
            }

        # 2. AST structural invariance test (whitespace / comment changes only)
        if old_fp and old_fp.ast_hash == new_fp.ast_hash:
            self.fingerprints[rel_path] = new_fp
            return {
                "action": "fingerprint_updated_only",
                "reason": "ast_invariant_whitespace_or_comments",
                "file": rel_path,
            }

        # 3. Structural AST logic change -> re-index file symbols
        self.fingerprints[rel_path] = new_fp
        parsed_file = self.symbol_index.index_file(full_path, force=True)
        if parsed_file and parsed_file.is_valid_syntax:
            classes_count = sum(1 for s in parsed_file.symbols if s.kind == "class")
            funcs_count = sum(
                1 for s in parsed_file.symbols if s.kind in ("function", "method")
            )
            return {
                "action": "reindexed_ast_and_symbols",
                "file": rel_path,
                "classes_count": classes_count,
                "functions_count": funcs_count,
            }

        return {"action": "parse_failed", "file": rel_path}
