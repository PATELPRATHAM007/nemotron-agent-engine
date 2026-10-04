"""
Centralized Web Templates & Frontend Integration
================================================
The user interface has transitioned to the dedicated Next.js frontend
application (nemotron-agent-frontend running at http://localhost:3000).

Server-side Jinja2 templates are deprecated in favor of the decoupled Next.js
client. This module exports `templates = None` for seamless backward compatibility
with app/routes/pages.py.
"""

from typing import Any

# Since the frontend is now Next.js, templates is intentionally None.
# If server-side Jinja2 templates are ever needed, initialize them here.
templates: Any = None

__all__ = ["templates"]
