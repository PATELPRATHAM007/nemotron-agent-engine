"""
Multi-Layer Knowledge Graph: Schema & Taxonomy
================================================
Defines rich multi-layer node taxonomy and semantic relationship edge types
for the Repository Knowledge Graph, separating WHAT from HOW and grounding
every fact in traceable evidence.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ConfidenceLevel(str, Enum):
    """Evidence confidence rating for graph nodes and assertions."""

    HIGH = "HIGH"          # Directly observed in code AST, schema, or test
    MEDIUM = "MEDIUM"      # Derived from config, routes, or conventions
    LOW = "LOW"            # Inferred from heuristic matching
    INFERRED = "INFERRED"  # Machine-inferred architectural hypothesis
    UNKNOWN = "UNKNOWN"    # Unverified assertion


class NodeKind(str, Enum):
    """Multi-Layer Node Hierarchy distinguishing WHAT from HOW."""

    # High-Level Semantic Layers (WHAT)
    PROJECT = "PROJECT"                      # Root multi-project ecosystem
    FEATURE = "FEATURE"                      # Stable business feature identity (e.g. feat.autonomous_mission)
    BUSINESS_CAPABILITY = "BUSINESS_CAPABILITY" # High-level organizational capability
    USER_FLOW = "USER_FLOW"                  # End-to-end user journey across UI, API, DB
    BUSINESS_RULE = "BUSINESS_RULE"          # Governed invariant or constraint
    STATE = "STATE"                          # Discrete lifecycle state (e.g. PLANNING, EXECUTING)
    EVENT = "EVENT"                          # Domain event or SSE telemetry packet
    ISSUE = "ISSUE"                          # Detected architectural flaw, dead code, or risk

    # Structural & Implementation Layers (HOW)
    REPOSITORY = "REPOSITORY"                # Physical git repository
    MODULE = "MODULE"                        # Package or folder namespace
    FILE = "FILE"                            # Source file (.py, .ts, .tsx, .css)
    SYMBOL = "SYMBOL"                        # Class, function, method, or constant
    FUNCTION = "FUNCTION"                    # Standalone or member function
    CLASS = "CLASS"                          # Class definition
    COMPONENT = "COMPONENT"                  # Frontend UI component (e.g. MissionControl.tsx)
    API_ENDPOINT = "API_ENDPOINT"            # HTTP / WebSocket endpoint
    DATABASE_ENTITY = "DATABASE_ENTITY"      # ORM Model or SQL table
    DEPENDENCY = "DEPENDENCY"                # Internal or third-party dependency
    TEST = "TEST"                            # Test case or suite
    ADR = "ADR"                              # Architecture Decision Record
    BUG = "BUG"                              # Historical defect or failure mode
    TABLE = "TABLE"                          # Relational table
    COLUMN = "COLUMN"                        # Database column
    INDEX = "INDEX"                          # Database index


class EdgeKind(str, Enum):
    """Rich semantic relationship edge types connecting graph entities."""

    # Semantic Realization & Implementation
    IMPLEMENTS = "IMPLEMENTS"                # Function / Service -> Business Rule / Capability
    REALIZES = "REALIZES"                    # Component / API -> User Flow
    IMPLEMENTS_RULE = "IMPLEMENTS_RULE"      # Code -> Business Rule
    CONSTRAINED_BY = "CONSTRAINED_BY"        # Flow / Feature -> Business Rule
    PART_OF_FEATURE = "PART_OF_FEATURE"      # Symbol / File -> Feature

    # Structural & Call Topology
    DEFINES = "DEFINES"                      # File -> Symbol / Component
    IMPORTS = "IMPORTS"                      # File -> File / Package
    CALLS = "CALLS"                          # Symbol -> Symbol / Tool
    CALLED_BY = "CALLED_BY"                  # Inverse call relation
    CONTAINS = "CONTAINS"                    # Module -> File / Class -> Method
    OWNS = "OWNS"                            # Project -> Repository / Feature
    EXTENDS = "EXTENDS"                      # Class inheritance
    PART_OF = "PART_OF"                      # Child -> Parent relation

    # API & Data Flow
    EXPOSES = "EXPOSES"                      # Service / Router -> API Endpoint
    EXPOSES_ROUTE = "EXPOSES_ROUTE"          # Route Handler -> Route Path
    CONSUMES = "CONSUMES"                    # UI / Client -> API Endpoint
    PRODUCES = "PRODUCES"                    # API / Agent -> Artifact / Event
    TRIGGERS = "TRIGGERS"                    # Action -> State Transition / Event
    LISTENS_TO = "LISTENS_TO"                # Hook / Handler -> Event Stream
    PERSISTS_TO = "PERSISTS_TO"              # Service -> Database Entity
    READS_FROM = "READS_FROM"                # Service / Query -> Table
    WRITES_TO = "WRITES_TO"                  # Service / Mutation -> Table
    MODELS_ENTITY = "MODELS_ENTITY"          # SQLAlchemy class -> Database Table
    QUERIES_TABLE = "QUERIES_TABLE"          # Repository -> Table
    INDEXES_COLUMN = "INDEXES_COLUMN"        # Index -> Column
    REFERENCES_TABLE = "REFERENCES_TABLE"    # Foreign Key -> Target Table

    # Security & Governance
    AUTHORIZES = "AUTHORIZES"                # Role / Token -> Feature / API
    REQUIRES_PERMISSION = "REQUIRES_PERMISSION" # Action -> Permission Gate
    VALIDATES = "VALIDATES"                  # Schema / Gate -> Input / Diff

    # State Transitions & Navigation
    TRANSITIONS_TO = "TRANSITIONS_TO"        # State A -> State B
    RENDERED_BY = "RENDERED_BY"              # View -> Component
    NAVIGATES_TO = "NAVIGATES_TO"            # Button / Route -> Page

    # Quality, Testing & Deployment
    TESTS = "TESTS"                          # Test -> Symbol / Feature
    TESTED_BY = "TESTED_BY"                  # Feature -> Test Suite
    CONFIGURED_BY = "CONFIGURED_BY"          # Service -> Env Variable / Settings
    DEPLOYED_AS = "DEPLOYED_AS"              # Service -> Docker Container / Cloud Pod
    INTEGRATES_WITH = "INTEGRATES_WITH"      # Engine -> Third-party service (vLLM, Groq)
    DEPENDS_ON = "DEPENDS_ON"                # Module / Package dependency
    DOCUMENTED_BY = "DOCUMENTED_BY"          # Feature -> ADR / Docs
    HAS_BUG = "HAS_BUG"                      # Feature -> Bug
    AFFECTS = "AFFECTS"                      # Blast radius / change impact


class GraphNode(BaseModel):
    """Generic Node in the Repository Knowledge Graph."""

    id: str = Field(description="Unique node identifier across the repository")
    name: str = Field(description="Display or short name")
    kind: NodeKind
    file_path: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    docstring: str | None = None
    confidence: ConfidenceLevel = ConfidenceLevel.HIGH
    evidence: str | None = None
    last_verified: str | None = None
    source_symbols: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def __hash__(self):
        return hash(self.id)


class GraphEdge(BaseModel):
    """Directed Relationship Edge in the Repository Knowledge Graph."""

    source_id: str
    target_id: str
    kind: EdgeKind
    weight: float = 1.0
    evidence: str | None = None
    confidence: ConfidenceLevel = ConfidenceLevel.HIGH
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
