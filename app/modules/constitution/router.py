"""
Constitution Module APIRouter
=============================
"""

from fastapi import APIRouter
from app.modules.constitution import apis
from app.modules.constitution.schemas import RuleDetailResponse, ScaffoldResponse

router = APIRouter(prefix="/constitution", tags=["Agent Constitution"])

router.add_api_route(
    "/scaffold",
    apis.scaffold_constitution,
    methods=["POST"],
    response_model=ScaffoldResponse,
    summary="Scaffold repository .agent/ constitution structure",
)

router.add_api_route(
    "/rules",
    apis.list_rules,
    methods=["GET"],
    summary="List available repository constitutional rules",
)

router.add_api_route(
    "/rules/{rule_name}",
    apis.get_rule_detail,
    methods=["GET"],
    response_model=RuleDetailResponse,
    summary="Retrieve rule markdown content",
)
