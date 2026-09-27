"""
Multi-Layer Knowledge Graph: Schema & Taxonomy
================================================
Defines 8-layer node taxonomy and relationship edge types for the Repository Knowledge Graph.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class NodeKind(str, Enum):
    """8-Layer Node Hierarchy."""

    REPOSITORY = "REPOSITORY"  # Root project node
    MODULE = "MODULE"  # Top-level and sub-packages (e.g. app.modules.agent)
    FILE = "FILE"  # Individual source file
    SYMBOL = "SYMBOL"  # Classes, functions, methods, routes
    FEATURE = "FEATURE"  # Business capability (e.g. Authentication, Model Streaming)
    TEST = "TEST"  # Test cases & suites
    ADR = "ADR"  # Architecture Decision Record
    BUG = "BUG"  # Documented historical bug or lesson
    TABLE = "TABLE"  # Database Table or Collection
    COLUMN = "COLUMN"  # Table Column or Field
    INDEX = "INDEX"  # Database Index (B-Tree, HNSW, etc.)


class EdgeKind(str, Enum):
    """Relationship edge types connecting graph entities."""

    DEFINES = "DEFINES"  # FILE -> SYMBOL
    IMPORTS = "IMPORTS"  # FILE -> FILE
    CALLS = "CALLS"  # SYMBOL -> SYMBOL
    PART_OF_FEATURE = "PART_OF_FEATURE"  # FILE / SYMBOL -> FEATURE
    TESTS = "TESTS"  # TEST -> SYMBOL / FEATURE
    DEPENDS_ON = "DEPENDS_ON"  # MODULE -> MODULE
    EXPOSES_ROUTE = "EXPOSES_ROUTE"  # SYMBOL -> FEATURE
    DOCUMENTED_BY = "DOCUMENTED_BY"  # FEATURE -> ADR
    HAS_BUG = "HAS_BUG"  # FEATURE -> BUG
    AFFECTS = "AFFECTS"  # General cross-layer impact
    MODELS_ENTITY = "MODELS_ENTITY"  # ORM Model -> Database Entity
    QUERIES_TABLE = "QUERIES_TABLE"  # Repository / Route -> Table
    INDEXES_COLUMN = "INDEXES_COLUMN"  # Index -> Column
    REFERENCES_TABLE = "REFERENCES_TABLE"  # Foreign Key -> Target Table


class GraphNode(BaseModel):
    """Generic Node in the Repository Knowledge Graph."""

    id: str = Field(description="Unique node identifier across the repository")
    name: str = Field(description="Display or short name")
    kind: NodeKind
    file_path: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    docstring: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def __hash__(self):
        return hash(self.id)


class GraphEdge(BaseModel):
    """Directed Relationship Edge in the Repository Knowledge Graph."""

    source_id: str
    target_id: str
    kind: EdgeKind
    weight: float = 1.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class FeatureSubgraph(BaseModel):
    """Bounded subgraph extracted for a specific feature and its immediate scope."""

    feature_id: str
    feature_name: str
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    primary_files: list[str] = Field(default_factory=list)
    dependency_files: list[str] = Field(default_factory=list)
    test_files: list[str] = Field(default_factory=list)
