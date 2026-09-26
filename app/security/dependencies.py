"""
Backward compatibility re-export. Real dependencies live in app.modules.auth.dependencies.
"""
from app.modules.auth.dependencies import (
    get_current_auth_context,
)

__all__ = [
    "get_current_auth_context",
]
