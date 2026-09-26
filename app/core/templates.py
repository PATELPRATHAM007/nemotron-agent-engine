"""
Centralized Jinja2 Templates Engine
===================================
Configures the Jinja2 template environment for the FastAPI application using
paths and settings defined in app.core.config.

Provides pre-configured template globals (project_name, version, model_name,
api_base, environment) so routes remain clean and declarative.
"""

from fastapi.templating import Jinja2Templates

from app.core.config import settings

# Initialize centralized Jinja2 templates instance
templates = Jinja2Templates(directory=str(settings.TEMPLATES_DIR))

# Register global context variables across all templates
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
