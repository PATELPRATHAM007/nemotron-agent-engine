"""
Intelligence Module Models
==========================
Data representations for Codebase Knowledge Graph and AST Symbols.
"""

from typing import Any
from pydantic import BaseModel, Field


class SymbolMetadata(BaseModel):
    name: str
    kind: str  # function, class, method, variable
    file_path: str
    line_number: int
    docstring: str = ""


class DependencyEdge(BaseModel):
    source: str
    target: str
    edge_type: str  # import, call, inherits
