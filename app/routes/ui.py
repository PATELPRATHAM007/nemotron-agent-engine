"""
Interactive Web UI & Mission Control Router (Jinja2 Templates)
=============================================================
Renders Jinja2 templates matching the doc-processing-service visual language
for chatting with NVIDIA Nemotron 3 Ultra and dispatching autonomous missions.
"""

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from app.core.config import settings

router = APIRouter(tags=["UI"])

templates_dir = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


@router.get("/ui", tags=["UI"], summary="Interactive Web UI Dashboard")
@router.get("/chat", tags=["UI"], summary="Interactive Web Chat")
def serve_ui(request: Request) -> Any:
    """Render the Jinja2 interactive UI template."""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "project_name": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "model_name": settings.NEMOTRON_MODEL_NAME,
            "api_base": settings.NEMOTRON_API_BASE,
            "environment": settings.ENVIRONMENT,
        },
    )
