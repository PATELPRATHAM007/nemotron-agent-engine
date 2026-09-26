"""
Auth Module
===========
Provides identity, authentication, session lifecycle, and agent enrollment.
"""


def __getattr__(name: str):
    if name == "router":
        from app.modules.auth.router import router
        return router
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["router"]
