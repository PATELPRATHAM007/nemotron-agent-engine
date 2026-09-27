"""
Database Intelligence Schemas
=============================
Defines relational, NoSQL, and vector database schemas, introspection metadata,
query analysis models, explain plan structures, and safety violation representations.
"""

from enum import Enum

from pydantic import BaseModel, Field


class DatabaseType(str, Enum):
    POSTGRESQL = "POSTGRESQL"
    MYSQL = "MYSQL"
    SQLITE = "SQLITE"
    MONGODB = "MONGODB"
    REDIS = "REDIS"
    PGVECTOR = "PGVECTOR"
    QDRANT = "QDRANT"
    NEO4J = "NEO4J"


class ColumnMetadata(BaseModel):
    name: str
    data_type: str
    primary_key: bool = False
    nullable: bool = True
    default: str | None = None
    foreign_key: str | None = None  # e.g., "customers.id"
    unique: bool = False


class IndexMetadata(BaseModel):
    name: str
    columns: list[str] = Field(default_factory=list)
    is_unique: bool = False
    index_type: str = "BTREE"  # BTREE, HASH, GIN, GIST, HNSW, IVFFLAT


class TableMetadata(BaseModel):
    table_name: str
    schema_name: str = "public"
    columns: dict[str, ColumnMetadata] = Field(default_factory=dict)
    indexes: list[IndexMetadata] = Field(default_factory=list)
    foreign_keys: list[dict[str, str]] = Field(default_factory=list)
    row_count_estimate: int = 0


class VectorCollectionMetadata(BaseModel):
    collection_name: str
    dimension: int = 1536
    distance_metric: str = "COSINE"  # COSINE, EUCLIDEAN, DOT_PRODUCT
    index_type: str = "HNSW"  # HNSW, IVFFLAT
    vector_column: str = "embedding"
    metadata_fields: list[str] = Field(default_factory=list)


class DatabaseSchemaSnapshot(BaseModel):
    database_type: DatabaseType
    database_name: str
    tables: dict[str, TableMetadata] = Field(default_factory=dict)
    vector_collections: dict[str, VectorCollectionMetadata] = Field(
        default_factory=dict
    )
    collections: dict[str, dict[str, str]] = Field(
        default_factory=dict
    )  # NoSQL collections


class QueryRiskLevel(str, Enum):
    SAFE = "SAFE"
    WARNING = "WARNING"
    DANGEROUS = "DANGEROUS"
    BLOCKED = "BLOCKED"


class QueryAnalysisReport(BaseModel):
    sql_query: str
    risk_level: QueryRiskLevel
    is_read_only: bool = True
    issues: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    detected_anti_patterns: list[str] = Field(default_factory=list)
    affected_tables: list[str] = Field(default_factory=list)
    estimated_cost: float | None = None


class ExplainPlanNode(BaseModel):
    node_type: str  # Seq Scan, Index Scan, Nested Loop, Hash Join, etc.
    relation_name: str | None = None
    cost_startup: float = 0.0
    cost_total: float = 0.0
    plan_rows: int = 0
    actual_time_ms: float | None = None
    filter_predicate: str | None = None
    index_name: str | None = None
    children: list["ExplainPlanNode"] = Field(default_factory=list)
