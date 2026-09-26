"""
Interactive Web UI & Mission Control Router (Jinja2 Templates)
=============================================================
Renders Jinja2 templates matching the doc-processing-service visual language
for chatting with NVIDIA Nemotron 3 Ultra and dispatching autonomous missions.
"""

from typing import Any

from fastapi import APIRouter, Request

from app.core.templates import templates

router = APIRouter(tags=["UI"])


@router.get("/ui", tags=["UI"], summary="Interactive Web UI Dashboard")
@router.get("/chat", tags=["UI"], summary="Interactive Web Chat")
def serve_ui(request: Request) -> Any:
    """Render the Jinja2 interactive UI template."""
    return templates.TemplateResponse(request=request, name="index.html")
