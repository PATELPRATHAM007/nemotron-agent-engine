"""
Code Fingerprinting Engine
===========================
Computes multi-dimensional fingerprints for code files to enable zero-cost
incremental re-indexing:
  1. file_hash: SHA-256 of raw file bytes (detects any file touch/modification)
  2. ast_hash:  Structural hash of canonical AST (invariant to whitespace & comments)
  3. symbol_hash: Hash of exported symbol signatures (detects public contract changes)
"""

import ast
import hashlib
import os
import time

from pydantic import BaseModel, Field


class CodeFingerprint(BaseModel):
    """Multi-dimensional code fingerprint representation."""

    file_path: str
    file_hash: str = Field(description="SHA-256 of raw file bytes")
    ast_hash: str = Field(description="SHA-256 of normalized canonical AST structure")
    symbol_hash: str = Field(
        description="SHA-256 of exported class/function signatures"
    )
    last_modified: float = Field(default_factory=time.time)


def compute_file_hash(content: bytes) -> str:
    """Compute SHA-256 of raw file content."""
    return hashlib.sha256(content).hexdigest()


def compute_ast_hash(tree: ast.AST | None) -> str:
    """
    Compute structural hash of canonical AST.
    Invariant to whitespace, comments, blank lines, and line numbers.
    """
    if tree is None:
        return hashlib.sha256(b"").hexdigest()
    try:
        # include_attributes=False strips lineno, col_offset, end_lineno, etc.
        canonical_str = ast.dump(tree, annotate_fields=False, include_attributes=False)
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()
    except (TypeError, ValueError, RecursionError):
        return hashlib.sha256(b"ast_dump_error").hexdigest()


def compute_symbol_hash(symbol_signatures: list[str]) -> str:
    """
    Compute hash of sorted symbol signatures.
    Detects when exported APIs or function parameter lists change.
    """
    sorted_sigs = sorted(symbol_signatures)
    combined = "\n".join(sorted_sigs)
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def fingerprint_file(
    file_path: str,
    code: str | None = None,
    tree: ast.AST | None = None,
    symbol_sigs: list[str] | None = None,
) -> CodeFingerprint:
    """Generate a complete CodeFingerprint for a given file."""
    if code is None:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        with open(file_path, "rb") as f:
            content_bytes = f.read()
        code_str = content_bytes.decode("utf-8", errors="replace")
    else:
        content_bytes = code.encode("utf-8")
        code_str = code

    file_h = compute_file_hash(content_bytes)

    if tree is None:
        try:
            tree = ast.parse(code_str, filename=file_path)
        except SyntaxError:
            tree = None

    ast_h = compute_ast_hash(tree)
    sym_h = compute_symbol_hash(symbol_sigs or [])
    mtime = os.path.getmtime(file_path) if os.path.exists(file_path) else time.time()

    return CodeFingerprint(
        file_path=file_path,
        file_hash=file_h,
        ast_hash=ast_h,
        symbol_hash=sym_h,
        last_modified=mtime,
    )
