"""
Import Resolution Engine
=========================
Resolves relative and absolute Python imports into normalized module paths,
and classifies dependencies as internal project modules or external packages.
"""

import os

from pydantic import BaseModel

from app.intelligence.indexing.ast_parser import ImportDefinition


class ResolvedImport(BaseModel):
    """Normalized resolved import target."""

    raw_module: str
    raw_name: str
    resolved_module: str
    target_symbol: str | None = None
    is_internal: bool = False
    alias: str | None = None
    lineno: int = 1


def resolve_relative_module(
    current_module_path: str, import_module: str, level: int
) -> str:
    """
    Resolve a relative import (from . import x or from ..foo import y)
    given the current dotted module path.
    """
    if level == 0:
        return import_module

    parts = current_module_path.split(".")
    # level 1 = current package (parts[:-1])
    # level 2 = parent package (parts[:-2])
    trim_count = level
    trim_count = min(trim_count, len(parts))

    base_parts = parts[:-trim_count] if trim_count > 0 else parts
    if import_module:
        resolved_parts = base_parts + import_module.split(".")
    else:
        resolved_parts = base_parts

    return ".".join(p for p in resolved_parts if p)


class ImportResolver:
    """Resolves imports against a project workspace root."""

    def __init__(self, workspace_root: str):
        self.workspace_root = os.path.abspath(workspace_root)
        self.internal_modules: set[str] = set()
        self._scan_internal_modules()

    def _scan_internal_modules(self):
        """Pre-scan workspace to catalog all internal Python module names."""
        for root, dirs, files in os.walk(self.workspace_root):
            # Skip hidden and venv directories
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
                    rel_p = os.path.relpath(full_p, self.workspace_root)
                    if rel_p.endswith(".py"):
                        mod_p = rel_p[:-3].replace(os.path.sep, ".")
                        mod_p = mod_p.removesuffix(".__init__")
                        self.internal_modules.add(mod_p)
                        # Also add top-level namespace (e.g. 'app')
                        parts = mod_p.split(".")
                        for i in range(1, len(parts)):
                            self.internal_modules.add(".".join(parts[:i]))

    def resolve(self, current_module: str, imp: ImportDefinition) -> ResolvedImport:
        """Resolve an import definition against the workspace."""
        if imp.level > 0:
            resolved_mod = resolve_relative_module(
                current_module, imp.module, imp.level
            )
        else:
            resolved_mod = imp.module

        # Check if internal project module
        is_internal = False
        target_sym = None

        if imp.is_from:
            # e.g. from app.core.config import settings
            candidate_full = f"{resolved_mod}.{imp.name}" if resolved_mod else imp.name
            if candidate_full in self.internal_modules:
                resolved_mod = candidate_full
                is_internal = True
            elif resolved_mod in self.internal_modules:
                target_sym = imp.name
                is_internal = True
        else:
            # e.g. import app.core.config
            if resolved_mod in self.internal_modules:
                is_internal = True

        return ResolvedImport(
            raw_module=imp.module,
            raw_name=imp.name,
            resolved_module=resolved_mod,
            target_symbol=target_sym,
            is_internal=is_internal,
            alias=imp.alias,
            lineno=imp.lineno,
        )
