"""
Database Intelligence, Performance & Safety Module
==================================================
Provides schema introspection, database knowledge graph integration,
query/ORM anti-pattern analysis, explain plan intelligence, safety guardrails,
and performance baselines.
"""

from app.modules.intelligence.database.explain_engine import ExplainPlanEngine
from app.modules.intelligence.database.graph_connector import DatabaseGraphConnector
from app.modules.intelligence.database.migration_generator import (
    SafeMigrationGenerator,
    SafeMigrationProposal,
    safe_migration_generator,
)
from app.modules.intelligence.database.performance_baseline import DatabasePerformanceBaseline
from app.modules.intelligence.database.query_analyzer import QueryAnalyzer
from app.modules.intelligence.database.safety_guard import (
    DatabaseSafetyGuard,
    DatabaseSafetyViolationError,
)
from app.modules.intelligence.database.schema import (
    ColumnMetadata,
    DatabaseSchemaSnapshot,
    DatabaseType,
    ExplainPlanNode,
    IndexMetadata,
    QueryAnalysisReport,
    QueryRiskLevel,
    TableMetadata,
    VectorCollectionMetadata,
)
from app.modules.intelligence.database.schema_introspect import DatabaseIntrospectionEngine

__all__ = [
    "ColumnMetadata",
    "DatabaseGraphConnector",
    "DatabaseIntrospectionEngine",
    "DatabasePerformanceBaseline",
    "DatabaseSafetyGuard",
    "DatabaseSafetyViolationError",
    "DatabaseSchemaSnapshot",
    "DatabaseType",
    "ExplainPlanEngine",
    "ExplainPlanNode",
    "IndexMetadata",
    "QueryAnalysisReport",
    "QueryAnalyzer",
    "QueryRiskLevel",
    "SafeMigrationGenerator",
    "SafeMigrationProposal",
    "TableMetadata",
    "VectorCollectionMetadata",
    "safe_migration_generator",
]

