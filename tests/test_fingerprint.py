"""
Tests for Multi-Dimensional Code Fingerprinting (Phase 1)
"""

import ast

from app.intelligence.indexing.fingerprint import (
    compute_ast_hash,
    compute_file_hash,
    compute_symbol_hash,
)

CODE_ORIGINAL = '''def calculate_total(items: list, tax_rate: float = 0.05) -> float:
    """Calculate total price with tax."""
    subtotal = sum(items)
    return subtotal * (1.0 + tax_rate)
'''

# Code with added whitespace, comments, and blank lines (AST invariant)
CODE_WHITESPACE_ONLY = '''# Added comment at top


def calculate_total(items: list, tax_rate: float = 0.05) -> float:
    """Calculate total price with tax."""
    
    # Another comment inside
    subtotal = sum(items)
    
    return subtotal * (1.0 + tax_rate)

# End of file comment
'''

# Code with modified signature / logic (AST & symbol changes)
CODE_SIGNATURE_CHANGED = '''def calculate_total(items: list, tax_rate: float = 0.05, discount: float = 0.0) -> float:
    """Calculate total price with tax and discount."""
    subtotal = sum(items) - discount
    return subtotal * (1.0 + tax_rate)
'''


def test_fingerprint_file_hash_changes_on_whitespace():
    h1 = compute_file_hash(CODE_ORIGINAL.encode("utf-8"))
    h2 = compute_file_hash(CODE_WHITESPACE_ONLY.encode("utf-8"))

    # Raw file bytes are different
    assert h1 != h2


def test_fingerprint_ast_hash_invariant_to_whitespace_and_comments():
    tree1 = ast.parse(CODE_ORIGINAL)
    tree2 = ast.parse(CODE_WHITESPACE_ONLY)

    ast_h1 = compute_ast_hash(tree1)
    ast_h2 = compute_ast_hash(tree2)

    # Invariant: Normalized canonical AST structure hash MUST be identical!
    assert ast_h1 == ast_h2


def test_fingerprint_ast_hash_changes_on_logic_change():
    tree1 = ast.parse(CODE_ORIGINAL)
    tree3 = ast.parse(CODE_SIGNATURE_CHANGED)

    ast_h1 = compute_ast_hash(tree1)
    ast_h3 = compute_ast_hash(tree3)

    assert ast_h1 != ast_h3


def test_fingerprint_symbol_hash_changes_on_signature_change():
    sig1 = ["def calculate_total(items: list, tax_rate: float = 0.05) -> float"]
    sig3 = [
        "def calculate_total(items: list, tax_rate: float = 0.05, discount: float = 0.0) -> float"
    ]

    sym_h1 = compute_symbol_hash(sig1)
    sym_h3 = compute_symbol_hash(sig3)

    assert sym_h1 != sym_h3
