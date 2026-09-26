---
name: query-optimization
category: database
description: Query performance engineering, index design, N+1 avoidance, and keyset pagination.
keywords: [sql, query, orm, index, n+1, pagination, performance, database]
---

# Database Query Optimization Skill

## 1. N+1 Query Elimination
- Never query database entities in a `for` loop.
- In SQLAlchemy: Use `selectinload` or `joinedload`.
  ```python
  stmt = select(Customer).options(selectinload(Customer.orders))
  ```

## 2. Sargable Predicates
- Keep filtered columns bare in `WHERE` clauses so B-Trees can be traversed.
- Bad: `WHERE UPPER(email) = 'ALICE@EXAMPLE.COM'`
- Good: `WHERE email = :email` (or create functional index on `UPPER(email)`).

## 3. Large Dataset Keyset Pagination
- Avoid `OFFSET 100000` because the engine must scan and discard 100k rows.
- Use keyset pagination:
  ```sql
  SELECT id, amount, created_at
  FROM orders
  WHERE id > :last_seen_id
  ORDER BY id ASC
  LIMIT 50;
  ```

## 4. Covering Indexes
- If a query only needs `(status, user_id, amount)`, build a composite index:
  ```sql
  CREATE INDEX idx_orders_status_user ON orders(status, user_id) INCLUDE (amount);
  ```
