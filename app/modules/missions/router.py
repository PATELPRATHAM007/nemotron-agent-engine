"""
Autonomous Mission Router
=========================
Mounts endpoint routes to apis.py handlers.
"""

from fastapi import APIRouter
from app.modules.missions import apis

router = APIRouter(prefix="/missions", tags=["Autonomous Missions"])

# Mission Lifecycle & Timeline
router.post("")(apis.create_mission)
router.get("")(apis.list_missions)
router.get("/{mission_id}")(apis.get_mission)
router.get("/{mission_id}/stream")(apis.stream_mission)
router.post("/{mission_id}/messages")(apis.send_mission_message)

# Interactive Decision Gating
router.post("/{mission_id}/plan/approve")(apis.approve_plan)
router.post("/{mission_id}/selection")(apis.submit_selection)
router.post("/{mission_id}/permissions")(apis.submit_permission)
router.post("/{mission_id}/stop")(apis.stop_mission)
router.post("/{mission_id}/rollback")(apis.rollback_mission)

# Multimodal & Artifacts
router.post("/{mission_id}/upload")(apis.upload_attachment)
router.get("/{mission_id}/diff")(apis.get_mission_diff)
router.get("/{mission_id}/artifacts")(apis.get_mission_artifacts)
