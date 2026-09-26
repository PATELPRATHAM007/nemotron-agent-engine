"""
Intelligence Module APIRouter
=============================
"""

from fastapi import APIRouter
from app.modules.intelligence import apis
from app.modules.intelligence.schemas import ImpactAnalysisResponse

router = APIRouter(prefix="/intelligence", tags=["Codebase Intelligence"])

router.add_api_route(
    "/graph",
    apis.get_graph_summary,
    methods=["GET"],
    summary="Codebase Dependency Graph summary",
)

router.add_api_route(
    "/impact",
    apis.analyze_impact,
    methods=["POST"],
    response_model=ImpactAnalysisResponse,
    summary="Calculate blast radius and impact scope",
)

router.add_api_route(
    "/database/sql-analyze",
    apis.analyze_sql,
    methods=["POST"],
    summary="Analyze SQL query AST",
)

router.add_api_route(
    "/database/schema",
    apis.extract_db_schema,
    methods=["GET"],
    summary="Extract repository database schema via AST",
)
