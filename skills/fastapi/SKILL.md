---
name: fastapi-development
category: web
description: FastAPI routing, dependency injection, async patterns, and standard envelope serialization.
keywords: [fastapi, api, route, endpoint, router, pydantic, request, response]
---

# FastAPI Development Skill

## 1. APIRouter Modularization
- Group related routes inside feature routers:
  ```python
  router = APIRouter(prefix="/api/v1/feature", tags=["feature"])
  ```

## 2. Standardized JSON Responses
- Always return standard payload envelopes:
  `{"status": "success", "data": ..., "meta": {"timestamp": ...}}`

## 3. Dependency Injection
- Inject database sessions and security context via `Depends(get_db_session)`.
