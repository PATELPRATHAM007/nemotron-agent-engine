"""
Model Gateway Module
====================
Provides model registry, capability matching, provider adapters, and audited execution.
"""


def __getattr__(name: str):
    if name in ("router", "admin_router"):
        from app.modules.gateway.router import admin_router, router
        if name == "router":
            return router
        return admin_router
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["router", "admin_router"]
