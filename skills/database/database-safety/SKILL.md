---
name: database-safety
category: database
description: Comprehensive procedural guide enforcing read-only default connections, mutation guardrails, reversible Alembic migrations, and Level 5 human approval gates.
keywords: [safety, migration, mutation, drop, truncate, approval, ddl, alembic, rollback, transaction, savepoint]
---

# Database Safety & Guardrails Skill

## 1. Default Read-Only Mode
- **Zero-Trust Connection Policy**: Database connections must default to READ-ONLY mode.
- Read operations (`SELECT`, `EXPLAIN`, schema introspection) are unprivileged and safe for autonomous agent execution.
- Read-only sessions must be instantiated with explicit transaction isolation:
  ```python
  async with async_session_maker() as session:
      await session.execute(text("SET TRANSACTION READ ONLY"))
      result = await session.execute(select(CodeSymbol).where(CodeSymbol.is_active == True))
  ```

## 2. Hard-Forbidden DDL & Destruction Guards
- **Strictly Prohibited**: The agent must NEVER issue destructive DDL or DML statements dynamically:
  - `DROP TABLE`, `DROP DATABASE`, `TRUNCATE`, `ALTER TABLE ... DROP COLUMN`.
- Destructive operations require creating dedicated, versioned Alembic migration scripts in `alembic/versions/`.
- All schema changes must be reversible with symmetric `upgrade()` and `downgrade()` functions.

## 3. Scope of Mutations & Level 5 Human Approval Gate
- **Unbounded Mutation Prevention**: `UPDATE` or `DELETE` without an explicit, indexed `WHERE` clause is strictly blocked.
- Every state-mutating operation requires:
  1. Explicit operation classification (`OPERATION_CLASS_MUTATING`).
  2. Level 5 authorization clearance with a verified `human_approval_token`.
  3. Pre-execution dry run with row count preview (`EXPLAIN` / `COUNT`).
  ```python
  # Safe mutating execution pattern
  if not approval_token or not verify_level_5_clearance(approval_token):
      raise PermissionError("Level 5 human approval token required for database mutation")
  ```

## 4. Reversible Alembic Migrations
- Migration files must test both directions before applying to avoid orphaned schema state:
  ```python
  def upgrade() -> None:
      op.add_column("missions", sa.Column("token_count", sa.Integer(), nullable=True))
      op.create_index("idx_missions_token_count", "missions", ["token_count"])

  def downgrade() -> None:
      op.drop_index("idx_missions_token_count", table_name="missions")
      op.drop_column("missions", "token_count")
  ```
- Use batched operations for SQLite compatibility (`op.batch_alter_table`).

## 5. Transaction Safety & Savepoints
- Always wrap multi-statement writes in atomic blocks with automatic rollback on error:
  ```python
  async with session.begin():
      try:
          async with session.begin_nested():  # Creates DB SAVEPOINT
              await session.execute(insert_stmt)
      except IntegrityError:
          # Nested rollback leaves outer transaction healthy
          logger.warning("Duplicate key detected, skipping insert...")
  ```
