"""
Autonomous Missions Module
==========================
Unified Autonomous Mission Chat, interactive state machine, permissions, and multimodal execution.
"""


def __getattr__(name: str):
    if name == "router":
        from app.modules.missions.router import router
        return router
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["router"]
