"""
Repository Intelligence: Indexing & AST Subsystem
"""

from app.intelligence.indexing.ast_parser import (
    CodeASTVisitor,
    ImportDefinition,
    ParsedModule,
    SymbolDefinition,
    derive_module_path,
    parse_python_file,
)
from app.intelligence.indexing.fingerprint import (
    CodeFingerprint,
    compute_ast_hash,
    compute_file_hash,
    compute_symbol_hash,
    fingerprint_file,
)
from app.intelligence.indexing.import_resolver import (
    ImportResolver,
    ResolvedImport,
    resolve_relative_module,
)
from app.intelligence.indexing.symbol_extractor import (
    SymbolIndex,
)
from app.intelligence.indexing.watcher import (
    IncrementalFileWatcher,
)

__all__ = [
    "CodeASTVisitor",
    "CodeFingerprint",
    "ImportDefinition",
    "ImportResolver",
    "IncrementalFileWatcher",
    "ParsedModule",
    "ResolvedImport",
    "SymbolDefinition",
    "SymbolIndex",
    "compute_ast_hash",
    "compute_file_hash",
    "compute_symbol_hash",
    "derive_module_path",
    "fingerprint_file",
    "parse_python_file",
    "resolve_relative_module",
]
