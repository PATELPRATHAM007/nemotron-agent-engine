"""
Cost Module Router
==================
Mounts cost and token analytics endpoints to apis.py handlers.
"""

from fastapi import APIRouter
from app.modules.cost import apis

router = APIRouter(prefix="/cost", tags=["Cost & Token Analytics"])

router.get("/summary")(apis.get_cost_summary)
router.get("/records")(apis.list_cost_records)
router.get("/{mission_id}")(apis.get_mission_cost)
router.post("/check-budget")(apis.check_budget)
