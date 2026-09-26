"""
Model Gateway Module
====================
Provides model registry, capability-based routing, and the 18-step verification pipeline.
"""

from app.modules.gateway.router import admin_router, router

__all__ = ["router", "admin_router"]
