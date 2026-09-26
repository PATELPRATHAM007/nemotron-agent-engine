"""
Validation Gate Schemas
=======================
Data structures for the 8-Gate Verification Pipeline.
"""

from enum import Enum

from pydantic import BaseModel, Field


class GateStatus(str, Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class GateResult(BaseModel):
    gate_id: int
    gate_name: str
    status: GateStatus
    message: str = ""
    error_details: str | None = None
    execution_time_ms: float = 0.0


class ValidationPipelineReport(BaseModel):
    all_passed: bool
    total_gates_evaluated: int
    passed_gates: int
    failed_gate: GateResult | None = None
    gate_results: list[GateResult] = Field(default_factory=list)
