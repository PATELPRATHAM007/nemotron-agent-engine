"""
Symbol Extractor & Index Catalog
=================================
Manages repository-wide symbol cataloging, indexing, and fast lookups.
Supports incremental updates using CodeFingerprints to avoid re-parsing unchanged files.
"""

import os

from app.intelligence.indexing.ast_parser import (
    ParsedModule,
    SymbolDefinition,
    parse_python_file,
)
from app.intelligence.indexing.fingerprint import fingerprint_file


class SymbolIndex:
    """Repository-level index of all parsed modules and symbols."""

    def __init__(self, workspace_root: str):
        self.workspace_root = os.path.abspath(workspace_root)
        self.modules: dict[str, ParsedModule] = {}  # file_path -> ParsedModule
        self.symbols_by_id: dict[str, SymbolDefinition] = {}
        self.symbols_by_name: dict[str, list[SymbolDefinition]] = {}
        self.routes: list[SymbolDefinition] = []

    def _register_module(self, parsed: ParsedModule):
        """Update index with symbols from a parsed module."""
        self.modules[parsed.file_path] = parsed
        for sym in parsed.symbols:
            self.symbols_by_id[sym.id] = sym
            self.symbols_by_name.setdefault(sym.name, []).append(sym)
            if sym.kind == "route" or sym.route_info is not None:
                self.routes.append(sym)

    def _unregister_file(self, file_path: str):
        """Remove symbols from an existing file before re-indexing."""
        if file_path in self.modules:
            old_mod = self.modules.pop(file_path)
            for sym in old_mod.symbols:
                self.symbols_by_id.pop(sym.id, None)
                if sym.name in self.symbols_by_name:
                    self.symbols_by_name[sym.name] = [
                        s
                        for s in self.symbols_by_name[sym.name]
                        if s.file_path != file_path
                    ]
            self.routes = [r for r in self.routes if r.file_path != file_path]

    def index_file(
        self, file_path: str, code: str | None = None, force: bool = False
    ) -> ParsedModule:
        """
        Incrementally index a single file.
        Checks if file fingerprint changed; if unchanged and not force, skips parsing.
        """
        abs_path = os.path.abspath(file_path)
        if not force and abs_path in self.modules:
            existing_fp = self.modules[abs_path].fingerprint
            # Quick check if mtime or size changed before reading
            if os.path.exists(abs_path):
                current_fp = fingerprint_file(abs_path, code=code)
                if current_fp.file_hash == existing_fp.file_hash:
                    # Unchanged!
                    return self.modules[abs_path]

        self._unregister_file(abs_path)
        parsed = parse_python_file(abs_path, code=code, root_dir=self.workspace_root)
        self._register_module(parsed)
        return parsed

    def index_workspace(self, force: bool = False) -> int:
        """Scan and index all Python files in the workspace. Returns count of files parsed."""
        parsed_count = 0
        for root, dirs, files in os.walk(self.workspace_root):
            dirs[:] = [
                d
                for d in dirs
                if not d.startswith(".")
                and d
                not in ("venv", ".venv", "node_modules", "__pycache__", "build", "dist")
            ]
            for f in files:
                if f.endswith(".py"):
                    full_p = os.path.join(root, f)
                    self.index_file(full_p, force=force)
                    parsed_count += 1
        return parsed_count

    def get_symbol(self, symbol_id: str) -> SymbolDefinition | None:
        """Lookup symbol by unique hierarchical ID."""
        return self.symbols_by_id.get(symbol_id)

    def find_by_name(self, name: str) -> list[SymbolDefinition]:
        """Find symbols matching a given name (e.g. 'execute_mission')."""
        return self.symbols_by_name.get(name, [])

    def find_by_kind(self, kind: str) -> list[SymbolDefinition]:
        """Find all symbols of a given kind (class, function, method, route)."""
        return [s for s in self.symbols_by_id.values() if s.kind == kind]

    def get_routes(self) -> list[SymbolDefinition]:
        """Return all detected API route symbols."""
        return list(self.routes)

    def total_symbols(self) -> int:
        """Return total count of indexed symbols."""
        return len(self.symbols_by_id)

    def total_files(self) -> int:
        """Return total count of indexed files."""
        return len(self.modules)
