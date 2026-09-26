"""
Auth Module Router
==================
Maps URL endpoints to controller handlers in apis.py.
"""

from fastapi import APIRouter, status
from app.modules.auth import apis

router = APIRouter(prefix="/auth", tags=["Identity & Authentication"])

# Identity & Session Lifecycle
router.post("/register", status_code=status.HTTP_201_CREATED)(apis.register)
router.post("/login")(apis.login)
router.post("/refresh")(apis.refresh_tokens)
router.post("/logout")(apis.logout)
router.get("/me")(apis.me)

# Sessions Management
router.get("/sessions")(apis.list_sessions)
router.delete("/sessions/{session_id}")(apis.revoke_session)

# Local Agent Identity Enrollment
router.post("/agents/register")(apis.register_agent)
