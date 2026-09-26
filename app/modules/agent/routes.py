"""
Backward Compatibility Layer for Agent Routes
=============================================
Re-exports router from app.modules.agent.router.
"""

from app.modules.agent.router import router

__all__ = ["router"]
