"""
Unified Exception & Error Diagnostics Hierarchy
==============================================
Provides structured, categorized domain exceptions for the repository intelligence engine.
Every exception includes:
  - error_code: Machine-readable uppercase token (e.g. ERR_SCOPE_VIOLATION)
  - component: Subsystem name where the error originated
  - http_status: Standard HTTP status code
  - details: Contextual diagnostic data (files, queries, line numbers)
  - suggested_fix: Clear, actionable instructions for human developers and Nemotron
"""

from typing import Any


class NemotronEngineError(Exception):
    """Root base exception for all repository intelligence engine errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "ERR_ENGINE_GENERAL",
        component: str = "core",
        http_status: int = 400,
        details: dict[str, Any] | None = None,
        suggested_fix: str = "",
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.component = component
        self.http_status = http_status
        self.details = details or {}
        self.suggested_fix = suggested_fix

    def to_dict(self) -> dict[str, Any]:
        """Serialize structured exception details for API and log consumption."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "component": self.component,
            "http_status": self.http_status,
            "details": self.details,
            "suggested_fix": self.suggested_fix,
        }


class ScopeViolationError(NemotronEngineError):
    """Raised when an agent attempts to modify files outside its authorized TaskScope."""

    def __init__(
        self,
        message: str,
        file_path: str = "",
        authorized_files: list[str] | None = None,
    ):
        self.file_path = file_path
        self.authorized_files = authorized_files or []
        super().__init__(
            message=message,
            error_code="ERR_SCOPE_VIOLATION",
            component="scope_lock",
            http_status=403,
            details={
                "file_path": self.file_path,
                "authorized_files": self.authorized_files,
            },
            suggested_fix="Submit an explicit Scope Expansion Request to authorize this file before modifying it.",
        )


class DatabaseSafetyViolationError(NemotronEngineError):
    """Raised when an operation breaches database safety boundaries."""

    def __init__(
        self, message: str, sql_command: str = "", risk_level: str = "BLOCKED"
    ):
        self.sql_command = sql_command
        self.risk_level = risk_level
        super().__init__(
            message=message,
            error_code="ERR_DATABASE_SAFETY",
            component="database_safety",
            http_status=403,
            details={"sql_command": self.sql_command, "risk_level": self.risk_level},
            suggested_fix="Ensure query is read-only, includes a WHERE clause, and has LEVEL 5 human approval token if mutating.",
        )


class PermissionDeniedError(NemotronEngineError):
    """Raised when an operation exceeds the active agent permission level."""

    def __init__(self, message: str, required_level: int = 0, current_level: int = 0):
        self.required_level = required_level
        self.current_level = current_level
        super().__init__(
            message=message,
            error_code="ERR_PERMISSION_DENIED",
            component="permissions",
            http_status=403,
            details={
                "required_level": self.required_level,
                "current_level": self.current_level,
            },
            suggested_fix="Upgrade active permission level or submit an approval token for this operation.",
        )


class ApprovalRequiredError(NemotronEngineError):
    """Raised when an operation requires an interactive human approval token."""

    def __init__(self, message: str, request_id: str = "", operation_type: str = ""):
        self.request_id = request_id
        self.operation_type = operation_type
        super().__init__(
            message=message,
            error_code="ERR_APPROVAL_REQUIRED",
            component="approval_gates",
            http_status=428,  # Precondition Required
            details={
                "request_id": self.request_id,
                "operation_type": self.operation_type,
            },
            suggested_fix="Submit authorization token via POST /api/v1/agent/approval/submit to proceed.",
        )


class ContextBudgetExceededError(NemotronEngineError):
    """Raised when prompt payload exceeds the maximum token ceiling."""

    def __init__(self, message: str, token_count: int = 0, max_tokens: int = 32000):
        self.token_count = token_count
        self.max_tokens = max_tokens
        super().__init__(
            message=message,
            error_code="ERR_CONTEXT_BUDGET_EXCEEDED",
            component="context_budget",
            http_status=413,  # Payload Too Large
            details={"token_count": self.token_count, "max_tokens": self.max_tokens},
            suggested_fix="Use HierarchicalContextBuilder to truncate dependencies to Level 2 signatures.",
        )


class CostBudgetExceededError(NemotronEngineError):
    """Raised when an operation or mission exceeds financial cost boundaries."""

    def __init__(
        self,
        message: str,
        current_cost_usd: float = 0.0,
        max_cost_usd: float = 1.0,
        currency: str = "USD",
    ):
        self.current_cost_usd = current_cost_usd
        self.max_cost_usd = max_cost_usd
        self.currency = currency
        super().__init__(
            message=message,
            error_code="ERR_COST_BUDGET_EXCEEDED",
            component="cost_analytics",
            http_status=402,  # Payment Required
            details={
                "current_cost_usd": self.current_cost_usd,
                "max_cost_usd": self.max_cost_usd,
                "currency": self.currency,
            },
            suggested_fix="Increase the mission/daily budget limit or optimize prompt token consumption.",
        )


class VerificationGateFailedError(NemotronEngineError):
    """Raised when an 8-Gate verification battery check fails."""

    def __init__(
        self, message: str, gate_id: int = 0, gate_name: str = "", error_trace: str = ""
    ):
        self.gate_id = gate_id
        self.gate_name = gate_name
        self.error_trace = error_trace
        super().__init__(
            message=message,
            error_code="ERR_GATE_VALIDATION_FAILED",
            component="verification_gates",
            http_status=422,  # Unprocessable Entity
            details={
                "gate_id": self.gate_id,
                "gate_name": self.gate_name,
                "error_trace": self.error_trace,
            },
            suggested_fix=f"Review and correct failures reported by Gate {gate_id} ({gate_name}).",
        )


class AutoDebugExhaustedError(NemotronEngineError):
    """Raised when auto-debugging attempts reach maximum bound and triggers rollback."""

    def __init__(self, message: str, attempts: int = 3, max_attempts: int = 3):
        self.attempts = attempts
        self.max_attempts = max_attempts
        super().__init__(
            message=message,
            error_code="ERR_AUTO_DEBUG_EXHAUSTED",
            component="auto_debugger",
            http_status=500,
            details={"attempts": self.attempts, "max_attempts": self.max_attempts},
            suggested_fix="Changes were automatically rolled back via Git. Inspect diagnostic logs for root cause.",
        )


class ASTParseError(NemotronEngineError):
    """Raised when AST parsing fails on invalid source syntax."""

    def __init__(self, message: str, file_path: str = "", line_number: int = 0):
        self.file_path = file_path
        self.line_number = line_number
        super().__init__(
            message=message,
            error_code="ERR_AST_PARSE",
            component="ast_parser",
            http_status=400,
            details={"file_path": self.file_path, "line_number": self.line_number},
            suggested_fix="Fix syntax errors in target file before re-attempting AST extraction.",
        )


class ToolExecutionError(NemotronEngineError):
    """Raised when an autonomous tool execution fails."""

    def __init__(
        self, message: str, tool_name: str = "", arguments: dict[str, Any] | None = None
    ):
        self.tool_name = tool_name
        self.arguments = arguments or {}
        super().__init__(
            message=message,
            error_code="ERR_TOOL_EXECUTION",
            component="tool_registry",
            http_status=500,
            details={"tool_name": self.tool_name, "arguments": self.arguments},
            suggested_fix="Check sandbox permissions, parameters, and tool preconditions.",
        )


class LLMGatewayError(NemotronEngineError):
    """Raised when LLM gateway streaming fails or times out."""

    def __init__(
        self, message: str, model_id: str = "nemotron-3-ultra", retry_count: int = 0
    ):
        self.model_id = model_id
        self.retry_count = retry_count
        super().__init__(
            message=message,
            error_code="ERR_LLM_GATEWAY",
            component="llm_gateway",
            http_status=503,  # Service Unavailable
            details={"model_id": self.model_id, "retry_count": self.retry_count},
            suggested_fix="Verify vLLM spot server endpoint connectivity and token limits.",
        )
