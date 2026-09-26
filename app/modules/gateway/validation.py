"""
Model Gateway Validation
========================
Validates model identifiers, capability specifications, and secret references.
"""

import re

VAULT_REF_PATTERN = re.compile(r"^vault://[a-zA-Z0-9_\-\./]+$")


class GatewayValidator:
    """Validates parameters, limits, and reference schemas for Model Gateway."""

    @staticmethod
    def validate_vault_reference(ref: str) -> str:
        clean = (ref or "").strip()
        if not clean.startswith("vault://"):
            clean = f"vault://{clean.lstrip('/')}"
        if not VAULT_REF_PATTERN.match(clean):
            raise ValueError(f"Invalid secret reference format: '{ref}'. Expected 'vault://path/to/key'")
        return clean

    @staticmethod
    def validate_capabilities(capabilities: list[str]) -> list[str]:
        valid_caps = {"text", "vision", "tools", "code", "reasoning", "embeddings"}
        cleaned = []
        for c in capabilities:
            cap = c.strip().lower()
            if cap in valid_caps:
                cleaned.append(cap)
        if not cleaned:
            cleaned = ["text"]
        return cleaned
