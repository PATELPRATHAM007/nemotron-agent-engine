"""
Cost Module
===========
Provides token cost calculation, persistent ledger tracking, and budget circuit breakers.
"""


def __getattr__(name: str):
    if name == "router":
        from app.modules.cost.router import router
        return router
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["router"]
