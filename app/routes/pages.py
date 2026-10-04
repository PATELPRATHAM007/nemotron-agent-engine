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


LANDING_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NVIDIA Nemotron 3 Ultra — Autonomous Mission Engine</title>
    <meta http-equiv="refresh" content="0; url=http://localhost:3000">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0c0a09; color: #f5f5f4; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; padding: 1.5rem; text-align: center; }
        .card { max-width: 520px; background: #1c1917; border: 1px solid #292524; border-radius: 1.5rem; padding: 2.5rem; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.5); }
        h1 { font-size: 1.5rem; font-weight: 800; margin-bottom: 0.5rem; color: #fff; }
        p { color: #a8a29e; font-size: 0.875rem; line-height: 1.6; margin-bottom: 1.5rem; }
        a.btn { display: inline-flex; align-items: center; gap: 0.5rem; background: #2563eb; color: #fff; text-decoration: none; padding: 0.75rem 1.5rem; border-radius: 0.75rem; font-weight: 600; font-size: 0.875rem; transition: background 0.15s; }
        a.btn:hover { background: #1d4ed8; }
        .badge { display: inline-block; padding: 0.25rem 0.75rem; border-radius: 9999px; background: rgba(16,185,129,0.1); color: #34d399; border: 1px solid rgba(16,185,129,0.2); font-size: 0.75rem; font-family: monospace; margin-bottom: 1rem; }
    </style>
</head>
<body>
    <div class="card">
        <span class="badge">NVIDIA Nemotron 3 Ultra • 550B LatentMoE</span>
        <h1>Autonomous Mission & Superuser Engine</h1>
        <p>The interactive mission control and superuser administration studio has transitioned to the dedicated Next.js frontend application (Autonomous Mission & Direct Chat).</p>
        <a href="http://localhost:3000" class="btn">Launch Next.js Mission Studio &rarr;</a>
        <div style="margin-top: 1.5rem; font-size: 0.75rem; color: #78716c;">
            Backend API: <a href="/docs" style="color: #60a5fa;">/docs</a> &bull; Health: <a href="/health" style="color: #34d399;">/health</a>
        </div>
    </div>
</body>
</html>"""


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
    if "text/html" in accept:
        if templates is not None and settings.TEMPLATES_DIR.exists():
            return templates.TemplateResponse(request=request, name="index.html")
        return HTMLResponse(content=LANDING_HTML)

    return {
        "service": settings.PROJECT_NAME,
        "status": "running",
        "docs": "/docs",
        "ui": "http://localhost:3000",
    }


@router.get("/ui", tags=["pages"], summary="Interactive Web UI Dashboard")
@router.get("/chat", tags=["pages"], summary="Interactive Web Chat")
def serve_ui(request: Request) -> Any:
    """Render the Jinja2 interactive UI template or Next.js redirect landing."""
    if templates is not None and settings.TEMPLATES_DIR.exists():
        return templates.TemplateResponse(request=request, name="index.html")
    return HTMLResponse(content=LANDING_HTML)



# Root level health probe for Docker / orchestrator readiness
router.add_api_route("/health", health_check, methods=["GET"], tags=["health"])
