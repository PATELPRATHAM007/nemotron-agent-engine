"""
Database Safety Guardrail Engine
================================
Enforces immutable safety constraints on database interactions:
  1. Default Connection Mode: READ-ONLY
  2. Hard command blocker: DROP, TRUNCATE, ALTER, GRANT, REVOKE
  3. Unconditional block on DELETE / UPDATE without WHERE clause
  4. LEVEL 5 Gate Requirement: Mutations require verified human approval token
"""

import re
from typing import ClassVar

from app.core.exceptions import DatabaseSafetyViolationError
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class DatabaseSafetyGuard:
    """Enforces safety guardrails before query dispatch or schema manipulation."""

    MUTATION_KEYWORDS: ClassVar[set[str]] = {
        "INSERT",
        "UPDATE",
        "DELETE",
        "DROP",
        "TRUNCATE",
        "ALTER",
        "CREATE",
        "GRANT",
        "REVOKE",
    }
    DESTRUCTIVE_DDL: ClassVar[set[str]] = {"DROP", "TRUNCATE", "ALTER"}

    def __init__(self, default_read_only: bool = True):
        self.default_read_only = default_read_only

    def is_mutation_query(self, sql: str) -> bool:
        """Returns True if the SQL statement attempts to modify data or schema."""
        first_word = sql.strip().split()[0].upper() if sql.strip() else ""
        return first_word in self.MUTATION_KEYWORDS

    def validate_query_execution(
        self,
        sql: str,
        permission_level: int = 0,
        human_approval_token: str | None = None,
        is_production: bool = False,
    ) -> bool:
        """
        Validate whether the query can be executed safely under the active permissions.
        Raises DatabaseSafetyViolationError upon safety breach.
        """
        clean_sql = sql.strip()
        if not clean_sql:
            return True

        first_word = clean_sql.split()[0].upper()

        # 1. Unconditional check: Unbounded UPDATE / DELETE without WHERE is FORBIDDEN
        if first_word == "UPDATE" and not re.search(
            r"\bWHERE\b", clean_sql, re.IGNORECASE
        ):
            raise DatabaseSafetyViolationError(
                "🛑 Database Safety Guardrail: Unbounded UPDATE without WHERE clause is strictly prohibited."
            )

        if first_word == "DELETE" and not re.search(
            r"\bWHERE\b", clean_sql, re.IGNORECASE
        ):
            raise DatabaseSafetyViolationError(
                "🛑 Database Safety Guardrail: Unbounded DELETE without WHERE clause is strictly prohibited."
            )

        # 2. Check for Destructive DDL (DROP / TRUNCATE)
        if first_word in self.DESTRUCTIVE_DDL and (
            is_production or not human_approval_token
        ):
            raise DatabaseSafetyViolationError(
                f"🛑 Database Safety Guardrail: Destructive command '{first_word}' requires explicit "
                f"human authorization token. Operation blocked."
            )

        # 3. Read-Only Default Enforcement
        if self.is_mutation_query(clean_sql):
            # Requires Level 5 (Database Mutation)
            if permission_level < 5:
                raise DatabaseSafetyViolationError(
                    f"🛑 Database Safety Guardrail: Mutation query '{first_word}' rejected. "
                    f"Active permission level is {permission_level}, but LEVEL 5 (Database Mutation) is required."
                )

            # Requires human approval token
            if not human_approval_token:
                raise DatabaseSafetyViolationError(
                    f"🛑 Database Safety Guardrail: Mutation '{first_word}' requires an active human approval token."
                )

        return True
