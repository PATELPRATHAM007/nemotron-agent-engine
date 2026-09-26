"""
Global Static Messages & User-Facing Strings
============================================
Single source of truth for common system messages across the platform.
Avoids hardcoding literal strings in route controllers and services.
"""

# Logging message templates
LOG_REQUEST_LINE = "%s %s -> %s in %.1fms (client=%s)"
LOG_REQUEST_EXCEPTION_LINE = "%s %s -> unhandled exception after %.1fms (client=%s)"
INTERNAL_SERVER_ERROR = "Internal server error"

# Health & System
HEALTH_CHECK_SUCCESS = "System is operational and healthy"
DATABASE_CONNECTED = "Database connection verified"
DATABASE_CONNECTION_FAILED = "Failed to connect to database"

# Authentication & Identity
AUTH_REGISTER_SUCCESS = "User registered successfully"
AUTH_LOGIN_SUCCESS = "Authentication successful"
AUTH_LOGIN_FAILED = "Invalid email or password"
AUTH_ACCOUNT_INACTIVE = "User account is inactive"
AUTH_TOKEN_EXPIRED = "Access token has expired or is invalid"
AUTH_REFRESH_SUCCESS = "Token refreshed successfully"
AUTH_TOKEN_REUSE_DETECTED = "Refresh token reuse detected. Session terminated."
AUTH_LOGOUT_SUCCESS = "Successfully logged out"
AUTH_SESSION_REVOKED = "Session revoked successfully"
AUTH_AGENT_REGISTERED = "Agent registered successfully"

# Authorization & Policies
AUTHZ_ACCESS_DENIED = "Access denied: insufficient permissions"
AUTHZ_TENANT_MISMATCH = "Cross-tenant access is strictly prohibited"
AUTHZ_APPROVAL_REQUIRED = "Action requires interactive approval"
AUTHZ_CRITICAL_BLOCKED = "Prohibited critical action blocked by policy"

# Model Gateway
GATEWAY_MODEL_NOT_FOUND = "Requested model is not registered"
GATEWAY_MODEL_UNAUTHORIZED = "Model is not authorized for your account or role"
GATEWAY_QUOTA_EXCEEDED = "Model quota or budget limit exceeded"
GATEWAY_STREAM_ERROR = "Model streaming error occurred"
GATEWAY_CREDENTIAL_ROTATED = "Provider credential rotated successfully"

# Missions & Engineering Agent
MISSION_CREATED = "Mission created successfully"
MISSION_NOT_FOUND = "Mission not found"
MISSION_PLAN_APPROVED = "Plan approved, beginning autonomous execution"
MISSION_SELECTION_RECORDED = "Selection decision recorded"
MISSION_PERMISSION_GRANTED = "Execution permission granted"
MISSION_PERMISSION_DENIED = "Execution permission denied"
MISSION_STOPPED = "Mission execution cancelled by user"
MISSION_ROLLBACK_SUCCESS = "Working tree reverted to clean git state"
MISSION_ATTACHMENT_UPLOADED = "Multimodal attachment uploaded successfully"

# Validation
VALIDATION_FAILED = "Request validation failed"
INVALID_IMAGE_HEADER = "Invalid image file header or unsupported format"
FILE_SIZE_EXCEEDED = "File size exceeds maximum allowed threshold"
PATH_TRAVERSAL_DETECTED = "Potentially malicious file path detected and sanitized"
SSRF_DETECTED = "URL destination rejected by SSRF protection policy"
