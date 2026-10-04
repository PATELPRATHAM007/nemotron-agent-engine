"""
Centralized Web Templates & Frontend Integration
================================================
NOTE: The interactive user interface has transitioned to the dedicated Next.js
frontend application (nemotron-agent-frontend running at http://localhost:3000).

This module provides an optional Jinja2 fallback if an 'app/templates' directory
is populated, or safely sets `templates = None` when the Next.js frontend is used.
Routes in app/routes/pages.py serve the Next.js landing bridge when templates is None.
"""

from typing import Any

from app.core.config import settings

templates: Any = None

# Optional Jinja2 initialization if templates directory exists
if settings.TEMPLATES_DIR.exists():
    try:
        from fastapi.templating import Jinja2Templates

        templates = Jinja2Templates(directory=str(settings.TEMPLATES_DIR))
        templates.env.globals.update(
            {
                "project_name": settings.PROJECT_NAME,
                "version": settings.VERSION,
                "model_name": settings.NEMOTRON_MODEL_NAME,
                "api_base": settings.NEMOTRON_API_BASE,
                "environment": settings.ENVIRONMENT,
                "enable_ui": settings.ENABLE_UI,
            }
        )
    except ImportError:
        templates = None

__all__ = ["templates"]
