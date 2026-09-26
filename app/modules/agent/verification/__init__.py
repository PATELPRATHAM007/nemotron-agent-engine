"""
Verification & Auto-Debugging Module
====================================
Provides 8-Gate verification and bounded auto-debugging with automated rollback.
"""

from app.modules.agent.verification.auto_debugger import (
    AutoDebugSession,
    BoundedAutoDebugger,
)
from app.modules.agent.verification.gates import VerificationPipeline
from app.modules.agent.verification.schema import (
    GateResult,
    GateStatus,
    ValidationPipelineReport,
)

__all__ = [
    "AutoDebugSession",
    "BoundedAutoDebugger",
    "GateResult",
    "GateStatus",
    "ValidationPipelineReport",
    "VerificationPipeline",
]
