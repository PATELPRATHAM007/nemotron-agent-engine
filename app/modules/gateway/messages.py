"""
Model Gateway Static Messages
=============================
Single source of truth for all messages returned by the model gateway subsystem.
"""

MODEL_NOT_FOUND = "Requested model is not registered"
MODEL_UNAUTHORIZED = "Model is not authorized for your account or role"
CAPABILITY_UNAUTHORIZED = "Required model capability is not authorized for your role"
QUOTA_EXCEEDED = "Model quota or budget limit exceeded for this organization"
RATE_LIMIT_EXCEEDED = "Rate limit exceeded for model generation. Please slow down."
CREDENTIAL_ROTATED = "Model provider credential rotated successfully"
PROVIDER_UNAVAILABLE = "Model provider is currently unreachable"
