---
name: database-safety
category: database
description: Enforces read-only default connections, mutation guardrails, and human approval gates.
keywords: [safety, migration, mutation, drop, truncate, approval, ddl]
---

# Database Safety & Guardrails Skill

## 1. Default Read-Only Mode
- All connections default to READ ONLY.
- Schema inspection, `EXPLAIN`, and `SELECT` are always safe.

## 2. Hard-Forbidden Commands
- Never issue `DROP TABLE`, `TRUNCATE`, or `ALTER TABLE` automatically.
- Reversible migrations must be created as code files first (e.g. Alembic versions).

## 3. Scope of Mutations
- Unbounded `UPDATE` or `DELETE` without a `WHERE` clause is strictly blocked.
- Any mutation requires `LEVEL 5` permission and a verified `human_approval_token`.

## 4. Rollback Readiness
- For every migration script, implement a verified `downgrade()` function before applying.
