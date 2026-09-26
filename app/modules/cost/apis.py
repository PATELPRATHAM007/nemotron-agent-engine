"""
Cost Module Endpoint Handlers (Controllers)
===========================================
Retrieves cost records, aggregates token analytics, and evaluates budget guardrails.
"""

from fastapi import Query
from app.modules.cost import messages
from app.modules.cost.schemas import BudgetCheckPayload
from app.modules.cost.service import budget_guard, cost_ledger, cost_tracker


async def get_cost_summary():
    """Retrieve aggregated token counts and costs."""
    summary = cost_ledger.get_summary()
    return {
        "success": True,
        "summary": summary.model_dump() if hasattr(summary, "model_dump") else summary,
        "message": messages.LEDGER_FETCHED,
    }


async def list_cost_records(
    limit: int = Query(50, ge=1, le=500),
):
    """List recent persistent cost reports from the ledger."""
    records = cost_ledger.get_recent_missions(limit=limit)
    return [r.model_dump() if hasattr(r, "model_dump") else r for r in records]


async def get_mission_cost(mission_id: str):
    """Get total cost and tokens for a specific mission."""
    cost_info = cost_tracker.get_mission_cost(mission_id)
    return {"mission_id": mission_id, "cost": cost_info}


async def check_budget(payload: BudgetCheckPayload):
    """Evaluate whether an upcoming turn would exceed budget limits."""
    # Check mission budget ceiling
    exceeded = (cost_tracker.current_cost() + payload.additional_cost_usd) > budget_guard.config.max_mission_budget_usd
    allowed = not exceeded
    return {
        "allowed": allowed,
        "mission_id": payload.mission_id,
        "message": "Within budget" if allowed else messages.BUDGET_EXCEEDED,
    }
