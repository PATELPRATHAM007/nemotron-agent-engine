"""
Codebase Intelligence Module
============================
AST parsing, dependency graphs, impact analysis, SQL understanding, and institutional memory.
"""


def __getattr__(name: str):
    if name == "router":
        from app.modules.intelligence.router import router
        return router
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["router"]
