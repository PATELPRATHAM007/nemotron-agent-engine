from typing import Any

from fastapi import APIRouter, Request

from app.api.v1.endpoints.health import health_check
from app.core.config import settings
from app.core.templates import templates

router = APIRouter(tags=["root"])


@router.get("/", tags=["root"])
def root(request: Request) -> Any:
    """Serve the modern web UI when accessed via browser,

    or return JSON service information for API clients.
    """
    accept = request.headers.get("accept", "")
    if "text/html" in accept and settings.TEMPLATES_DIR.exists():
        return templates.TemplateResponse(request=request, name="index.html")

    return {
        "service": settings.PROJECT_NAME,
        "status": "running",
        "docs": "/docs",
        "ui": "/ui",
    }


# Also expose /health at root level for orchestrator/docker health probes
router.add_api_route("/health", health_check, methods=["GET"], tags=["health"])
