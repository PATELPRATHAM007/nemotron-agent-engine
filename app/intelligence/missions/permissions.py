"""
Fine-Grained Permission & Risk System for Autonomous Missions
============================================================
Implements:
  - Action representation: action(target)
  - Allow / Ask / Deny precedence: DENY > ASK > ALLOW
  - Scopes: ONCE, MISSION, PROJECT, ALWAYS
  - Risk Classification: SAFE, LOW, MEDIUM, HIGH, CRITICAL
  - Never hide commands before execution
"""

from enum import Enum
import re
from typing import Any


class RiskLevel(str, Enum):
    SAFE = "SAFE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class PermissionDecision(str, Enum):
    DENY = "DENY"
    ASK = "ASK"
    ALLOW = "ALLOW"


class PermissionScope(str, Enum):
    ONCE = "ONCE"
    MISSION = "MISSION"
    PROJECT = "PROJECT"
    ALWAYS = "ALWAYS"


# Commands that are strictly prohibited (CRITICAL risk)
CRITICAL_PATTERNS = [
    r"\brm\s+-(?:[a-zA-Z]*[rf][a-zA-Z]*)\s+(?:/|~|\.\.)(?:\s|$)",
    r"\bmkfs\b",
    r"\bdd\s+if=",
    r"\bformat\s+[a-z]:",
    r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:",  # Fork bomb
    r"\bdrop\s+database\b",
    r"\bshutdown\b",
    r"\breboot\b",
]

# Commands with HIGH risk (require explicit approval unless pre-granted)
HIGH_RISK_PATTERNS = [
    r"\bgit\s+push\b",
    r"\bgit\s+reset\s+--hard\b",
    r"\bgit\s+clean\s+-fdx?\b",
    r"\bdocker\s+run\s+.*--privileged\b",
    r"\bchmod\s+777\b",
    r"\bchown\b",
    r"\bcurl\s+.*\|\s*(?:bash|sh)\b",
]

# Commands with MEDIUM risk (package installations, migrations)
MEDIUM_RISK_PATTERNS = [
    r"\bnpm\s+(?:install|i|update|remove|uninstall)\b",
    r"\bpip\s+(?:install|uninstall)\b",
    r"\byarn\s+(?:add|remove)\b",
    r"\bpoetry\s+(?:add|remove)\b",
    r"\balembic\s+(?:upgrade|downgrade)\b",
    r"\bdocker\s+compose\s+(?:up|down)\b",
    r"\bkill\b",
]

# Commands with LOW risk (tests, builds, lints)
LOW_RISK_PATTERNS = [
    r"\b(?:pytest|npm\s+test|python\s+-m\s+unittest|go\s+test|cargo\s+test)\b",
    r"\b(?:ruff|flake8|black|eslint|mypy|prettier)\b",
    r"\b(?:npm\s+run\s+build|cargo\s+build|tsc)\b",
    r"\bgit\s+(?:commit|checkout|branch|merge|stash)\b",
]

# Commands with SAFE risk (read-only queries)
SAFE_PATTERNS = [
    r"\bgit\s+(?:status|diff|log|branch\s+-a|show)\b",
    r"\b(?:ls|pwd|cat|head|tail|grep|find|tree|echo)\b",
    r"\bpython\s+--version\b",
    r"\bnode\s+--version\b",
]


class CommandRiskClassifier:
    """Classifies risk level of terminal commands and operations."""

    @staticmethod
    def classify_command(cmd: str) -> RiskLevel:
        normalized = cmd.strip()

        for pattern in CRITICAL_PATTERNS:
            if re.search(pattern, normalized, re.IGNORECASE):
                return RiskLevel.CRITICAL

        for pattern in HIGH_RISK_PATTERNS:
            if re.search(pattern, normalized, re.IGNORECASE):
                return RiskLevel.HIGH

        for pattern in MEDIUM_RISK_PATTERNS:
            if re.search(pattern, normalized, re.IGNORECASE):
                return RiskLevel.MEDIUM

        for pattern in LOW_RISK_PATTERNS:
            if re.search(pattern, normalized, re.IGNORECASE):
                return RiskLevel.LOW

        for pattern in SAFE_PATTERNS:
            if re.search(pattern, normalized, re.IGNORECASE):
                return RiskLevel.SAFE

        # Default fallback: inspect if modifying or executing
        if any(token in normalized for token in ["rm", "mv", "cp", "chmod", "curl", "wget"]):
            return RiskLevel.HIGH
        return RiskLevel.LOW


class MissionPermissionEngine:
    """Fine-grained permission manager enforcing Allow/Ask/Deny and scopes."""

    def __init__(self, workspace_root: str = "."):
        self.workspace_root = workspace_root
        self._mission_grants: dict[str, set[str]] = {}  # mission_id -> set of granted actions
        self._project_grants: set[str] = set()  # set of granted actions for project

    def grant(self, mission_id: str, action_target: str, scope: PermissionScope) -> None:
        """Record granted permission under requested scope."""
        if scope in (PermissionScope.PROJECT, PermissionScope.ALWAYS):
            self._project_grants.add(action_target)
        elif scope == PermissionScope.MISSION:
            if mission_id not in self._mission_grants:
                self._mission_grants[mission_id] = set()
            self._mission_grants[mission_id].add(action_target)

    def evaluate_command(
        self,
        mission_id: str,
        command: str,
        reason: str,
        directory: str = ".",
    ) -> dict[str, Any]:
        """
        Evaluate command permission.
        Returns:
          decision: ALLOW | ASK | DENY
          risk_level: SAFE | LOW | MEDIUM | HIGH | CRITICAL
          action_repr: e.g. "command(npm install)"
          reason: explanation
        """
        risk = CommandRiskClassifier.classify_command(command)
        action_repr = f"command({command})"

        # DENY takes top precedence: CRITICAL is always denied
        if risk == RiskLevel.CRITICAL:
            return {
                "decision": PermissionDecision.DENY.value,
                "risk_level": risk.value,
                "action": "command",
                "target": command,
                "action_repr": action_repr,
                "reason": f"Dangerous command blocked: violates safety policy.",
                "directory": directory,
            }

        # Check existing grants (project or mission scope)
        if action_repr in self._project_grants or (
            mission_id in self._mission_grants and action_repr in self._mission_grants[mission_id]
        ):
            return {
                "decision": PermissionDecision.ALLOW.value,
                "risk_level": risk.value,
                "action": "command",
                "target": command,
                "action_repr": action_repr,
                "reason": f"Allowed by pre-existing scope grant.",
                "directory": directory,
            }

        # SAFE commands are automatically allowed
        if risk == RiskLevel.SAFE:
            return {
                "decision": PermissionDecision.ALLOW.value,
                "risk_level": risk.value,
                "action": "command",
                "target": command,
                "action_repr": action_repr,
                "reason": "Safe read-only command.",
                "directory": directory,
            }

        # LOW risk commands (like pytest or ruff) in development are allowed unless configured otherwise
        if risk == RiskLevel.LOW:
            return {
                "decision": PermissionDecision.ALLOW.value,
                "risk_level": risk.value,
                "action": "command",
                "target": command,
                "action_repr": action_repr,
                "reason": reason or "Low-risk testing/inspection command.",
                "directory": directory,
            }

        # MEDIUM and HIGH risk require user approval
        return {
            "decision": PermissionDecision.ASK.value,
            "risk_level": risk.value,
            "action": "command",
            "target": command,
            "action_repr": action_repr,
            "reason": reason or "Command requires explicit human authorization.",
            "directory": directory,
        }

    def evaluate_file_write(
        self,
        mission_id: str,
        filepath: str,
        reason: str,
    ) -> dict[str, Any]:
        """Evaluate file write safety."""
        action_repr = f"write_file({filepath})"
        # Check if outside workspace
        is_outside = filepath.startswith("/") and not filepath.startswith(self.workspace_root)
        risk = RiskLevel.HIGH if is_outside else RiskLevel.LOW

        if is_outside:
            return {
                "decision": PermissionDecision.ASK.value,
                "risk_level": risk.value,
                "action": "write_file",
                "target": filepath,
                "action_repr": action_repr,
                "reason": "File modification outside repository workspace root requires authorization.",
                "directory": ".",
            }

        return {
            "decision": PermissionDecision.ALLOW.value,
            "risk_level": risk.value,
            "action": "write_file",
            "target": filepath,
            "action_repr": action_repr,
            "reason": reason or "Safe workspace file modification.",
            "directory": ".",
        }


mission_permissions = MissionPermissionEngine()
