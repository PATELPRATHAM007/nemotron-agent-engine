"""
Frontend Page Routes (HTML)
===========================
Serves server-rendered HTML pages, interactive mission control dashboard,
lightweight SVG favicon, and root service discovery.
Modeled after ad-automation-be app/routes/pages.py.
"""

from typing import Any
from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse

from app.api.v1.endpoints.health import health_check
from app.core.config import settings
from app.core.templates import templates

router = APIRouter(tags=["pages"])

FAVICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <rect width="100" height="100" rx="20" fill="#111111"/>
  <text x="50%" y="54%" text-anchor="middle" dominant-baseline="middle" font-size="62">⚡</text>
</svg>"""


@router.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    """Serve lightweight SVG favicon to avoid browser 404 errors."""
    return Response(content=FAVICON_SVG, media_type="image/svg+xml")


@router.get("/", tags=["pages"])
def home(request: Request) -> Any:
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


@router.get("/ui", tags=["pages"], summary="Interactive Web UI Dashboard")
@router.get("/chat", tags=["pages"], summary="Interactive Web Chat")
def serve_ui(request: Request) -> Any:
    """Render the Jinja2 interactive UI template."""
    return templates.TemplateResponse(request=request, name="index.html")


# Root level health probe for Docker / orchestrator readiness
router.add_api_route("/health", health_check, methods=["GET"], tags=["health"])
