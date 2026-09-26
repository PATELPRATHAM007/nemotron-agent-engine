"""
Database Intelligence, Performance & Safety Module
==================================================
Provides schema introspection, database knowledge graph integration,
query/ORM anti-pattern analysis, explain plan intelligence, safety guardrails,
and performance baselines.
"""

from app.intelligence.database.explain_engine import ExplainPlanEngine
from app.intelligence.database.graph_connector import DatabaseGraphConnector
from app.intelligence.database.performance_baseline import DatabasePerformanceBaseline
from app.intelligence.database.query_analyzer import QueryAnalyzer
from app.intelligence.database.safety_guard import (
    DatabaseSafetyGuard,
    DatabaseSafetyViolationError,
)
from app.intelligence.database.schema import (
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
from app.intelligence.database.schema_introspect import DatabaseIntrospectionEngine

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
    "TableMetadata",
    "VectorCollectionMetadata",
]
