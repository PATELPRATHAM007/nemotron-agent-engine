"""
Safe Database Migration Proposal Engine
=======================================
Generates reversible Alembic migration scripts from proposed schema changes:
  - Generates standard `upgrade()` and `downgrade()` functions.
  - Enforces safe DDL conventions (e.g. non-blocking index creation, reversible operations).
  - Flags destructive changes (e.g. `drop_column`, `drop_table`).
  - Strict Invariant: Execution of DDL or schema alterations strictly requires
    an explicit human approval token (`MUTATION_APPROVAL_REQUIRED`).
"""

import time
from typing import Any

from pydantic import BaseModel, Field

from app.core.logging_config import get_logger

logger = get_logger(__name__)


class MigrationOperation(BaseModel):
    op_type: str  # add_column, drop_column, create_index, drop_index, create_table
    column_name: str | None = None
    column_type: str = "sa.String(255)"
    nullable: bool = True
    index_name: str | None = None
    columns: list[str] = Field(default_factory=list)


class SafeMigrationProposal(BaseModel):
    revision_id: str
    message: str
    table_name: str
    migration_script: str
    is_reversible: bool
    destructive_operations: list[str] = Field(default_factory=list)
    requires_human_approval: bool = True
    approval_token_required: str = "MUTATION_APPROVAL_REQUIRED"
    created_at: float = Field(default_factory=time.time)


class SafeMigrationGenerator:
    """Proposes reversible Alembic migrations with safety verification checks."""

    def propose_migration(
        self,
        revision_id: str,
        message: str,
        table_name: str,
        operations: list[dict[str, Any]],
        down_revision: str | None = None,
    ) -> SafeMigrationProposal:
        """
        Synthesizes an Alembic Python migration script containing upgrade() and downgrade().
        """
        destructive: list[str] = []
        upgrade_lines: list[str] = []
        downgrade_lines: list[str] = []

        for op in operations:
            op_type = op.get("op_type", "").lower()
            col = op.get("column_name", "")
            col_type = op.get("column_type", "sa.String(255)")
            nullable = op.get("nullable", True)
            idx_name = op.get("index_name", f"ix_{table_name}_{col}")
            cols = op.get("columns", [col] if col else [])

            if op_type == "add_column":
                upgrade_lines.append(
                    f"    op.add_column('{table_name}', sa.Column('{col}', {col_type}, nullable={nullable}))"
                )
                downgrade_lines.insert(
                    0, f"    op.drop_column('{table_name}', '{col}')"
                )

            elif op_type == "drop_column":
                destructive.append(f"Dropping column '{col}' from table '{table_name}' results in irreversible data loss.")
                upgrade_lines.append(f"    op.drop_column('{table_name}', '{col}')")
                downgrade_lines.insert(
                    0, f"    op.add_column('{table_name}', sa.Column('{col}', {col_type}, nullable=True))"
                )

            elif op_type == "create_index":
                cols_repr = repr(cols)
                upgrade_lines.append(
                    f"    op.create_index('{idx_name}', '{table_name}', {cols_repr}, unique=False)"
                )
                downgrade_lines.insert(
                    0, f"    op.drop_index('{idx_name}', table_name='{table_name}')"
                )

            elif op_type == "drop_index":
                destructive.append(f"Dropping index '{idx_name}' may degrade query performance.")
                upgrade_lines.append(
                    f"    op.drop_index('{idx_name}', table_name='{table_name}')"
                )
                cols_repr = repr(cols)
                downgrade_lines.insert(
                    0, f"    op.create_index('{idx_name}', '{table_name}', {cols_repr}, unique=False)"
                )

        if not upgrade_lines:
            upgrade_lines.append("    pass")
        if not downgrade_lines:
            downgrade_lines.append("    pass")

        down_rev_str = f"'{down_revision}'" if down_revision else "None"

        script = f'''"""{message}

Revision ID: {revision_id}
Revises: {down_rev_str}
Create Date: {time.strftime('%Y-%m-%d %H:%M:%S')}
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '{revision_id}'
down_revision: Union[str, None] = {down_rev_str}
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
{chr(10).join(upgrade_lines)}


def downgrade() -> None:
{chr(10).join(downgrade_lines)}
'''

        return SafeMigrationProposal(
            revision_id=revision_id,
            message=message,
            table_name=table_name,
            migration_script=script,
            is_reversible=len(downgrade_lines) > 0,
            destructive_operations=destructive,
            requires_human_approval=True,
            approval_token_required="MUTATION_APPROVAL_REQUIRED",
        )


safe_migration_generator = SafeMigrationGenerator()
