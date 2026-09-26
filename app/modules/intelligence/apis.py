"""
Intelligence Module Controllers (API Endpoints)
===============================================
"""

from fastapi import Query
from app.modules.intelligence import messages
from app.modules.intelligence.schemas import (
    ASTSymbolQueryPayload,
    ImpactAnalysisPayload,
    ImpactAnalysisResponse,
    QueryAnalysisPayload,
)
from app.modules.intelligence.service import (
    DatabaseIntrospectionEngine,
    ImpactAnalyzer,
    QueryAnalyzer,
    RepoGraph,
    parse_python_file,
)
from app.modules.intelligence.validation import IntelligenceValidator


async def get_graph_summary():
    """Return dependency graph nodes and edges count."""
    graph = RepoGraph()
    return {
        "success": True,
        "nodes_count": len(graph.nodes),
        "edges_count": sum(len(e) for e in graph._out_edges.values()),
        "message": messages.GRAPH_EXTRACTED,
    }


async def analyze_impact(payload: ImpactAnalysisPayload, workspace_root: str = "."):
    """Calculate blast radius and affected files for changed files."""
    for f in payload.changed_files:
        IntelligenceValidator.validate_file_path(f, workspace_root)

    analyzer = ImpactAnalyzer(workspace_root=workspace_root)
    affected = analyzer.calculate_blast_radius(payload.changed_files, max_depth=payload.depth)
    return ImpactAnalysisResponse(
        success=True,
        affected_files=list(affected),
        risk_level="HIGH" if len(affected) > 10 else "LOW",
        message=messages.IMPACT_ANALYSIS_SUCCESS,
    )


async def analyze_sql(payload: QueryAnalysisPayload):
    """Analyze a SQL query AST for tables, columns, operations, and risk."""
    analyzer = QueryAnalyzer()
    analysis = analyzer.analyze(payload.sql)
    return {
        "success": True,
        "analysis": analysis,
        "message": messages.QUERY_ANALYSIS_SUCCESS,
    }


async def extract_db_schema():
    """Extract database tables and column definitions via schema introspection."""
    from app.db.session import engine
    introspector = DatabaseIntrospectionEngine()
    snapshot = introspector.introspect_relational_engine(engine)
    return {
        "success": True,
        "schema": snapshot.model_dump() if hasattr(snapshot, "model_dump") else snapshot,
        "message": messages.DATABASE_SCHEMA_EXTRACTED,
    }
