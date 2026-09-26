---
name: query-optimization
category: database
description: Comprehensive procedural guide for SQL query performance engineering, index design, N+1 query elimination, keyset pagination, and execution plan analysis.
keywords: [sql, query, orm, index, n+1, pagination, performance, database, selectinload, joinedload, sargable, explain]
---

# Database Query Optimization Skill

## 1. N+1 Query Elimination
- **Anti-Pattern**: Never execute ORM entity queries inside iterative loops (`for item in results:`).
- In SQLAlchemy 2.0, explicitly load related relationships using execution options:
  - **`selectinload`**: Use for 1-to-many and many-to-many relationships (issues a clean `WHERE id IN (...)` query):
    ```python
    stmt = (
        select(Mission)
        .options(selectinload(Mission.steps))
        .where(Mission.status == "completed")
    )
    results = (await session.execute(stmt)).scalars().all()
    ```
  - **`joinedload`**: Use for 1-to-1 and many-to-1 relationships (creates a single `LEFT OUTER JOIN`).

## 2. Sargable Predicates & Index Traversal
- Keep filtered columns bare in `WHERE` clauses so B-Trees can be traversed directly.
- **Un-sargable (Table Scan)**: Wrapping columns in SQL functions prevents index usage:
  - Bad: `WHERE UPPER(email) = 'ALICE@EXAMPLE.COM'`
  - Bad: `WHERE DATE(created_at) = '2026-09-26'`
- **Sargable (Index Seek)**:
  - Good: `WHERE email = :email` (with case-insensitive collation or lowercased ingestion)
  - Good: `WHERE created_at >= '2026-09-26 00:00:00' AND created_at < '2026-09-27 00:00:00'`

## 3. High-Volume Keyset Pagination
- **Anti-Pattern**: Avoid high `OFFSET` (e.g., `LIMIT 50 OFFSET 100000`) because the database engine must scan and discard 100k rows.
- **Keyset Cursor Pagination**:
  ```sql
  SELECT id, mission_id, tokens_used, created_at
  FROM cost_records
  WHERE (created_at, id) < (:cursor_created_at, :cursor_id)
  ORDER BY created_at DESC, id DESC
  LIMIT 50;
  ```

## 4. Composite & Covering Indexes (Left-Prefix Rule)
- When queries filter on multiple columns, build composite indexes adhering to the Left-Prefix Rule:
  1. Equality columns first: `WHERE tenant_id = :tid`
  2. Range / Inequality columns next: `AND created_at > :start`
  3. Sort columns last: `ORDER BY created_at DESC`
  ```sql
  CREATE INDEX idx_tenant_created ON audit_logs(tenant_id, created_at DESC);
  ```
- **Covering Index**: Include projected columns with `INCLUDE (...)` (PostgreSQL) to satisfy queries purely from the index tree without table heap lookups.

## 5. Query Profiling with EXPLAIN
- Always run `EXPLAIN (ANALYZE, BUFFERS)` in staging before deploying complex queries.
- Key red flags to investigate:
  - `Seq Scan` (Sequential scan on tables with >10,000 rows).
  - High `Buffers: shared hit=... read=...` indicating excessive disk I/O.
  - Sort operations using `external merge Disk` instead of memory.
