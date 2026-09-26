"""
Server-rendered web routes (HTML), matching ad-automation-be pattern.
"""

from app.routes.pages import router as pages_router

# Backward compatibility aliases
root_router = pages_router
ui_router = pages_router

__all__ = ["pages_router", "root_router", "ui_router"]
