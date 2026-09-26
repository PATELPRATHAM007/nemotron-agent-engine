---
name: fastapi-development
category: web
description: Comprehensive procedural guide for building production-grade FastAPI applications, covering async event loop hygiene, dependency injection, Pydantic v2 schemas, standard response envelopes, and SSE streaming.
keywords: [fastapi, api, route, endpoint, router, pydantic, request, response, dependency, sse, streaming, middleware]
---

# FastAPI Production Engineering Skill

## 1. Modular APIRouter Architecture
- Always group related endpoints into modular routers within `app/modules/<domain>/routes.py` or `app/api/v1/endpoints/`.
- Centralize routing mounts in `app/core/routers.py` under the global API prefix (e.g. `/api/v1`).
- Provide explicit `tags`, `summary`, and `response_model` on every route decorator:
  ```python
  router = APIRouter(prefix="/missions", tags=["Agent Missions"])

  @router.post(
      "/run",
      response_model=StandardResponse[MissionResponse],
      summary="Dispatch autonomous coding mission",
  )
  async def run_mission(payload: MissionRequest, db: AsyncSession = Depends(get_db)):
      ...
  ```

## 2. Async vs Sync Route Handler Hygiene (CRITICAL)
- **Use `async def` ONLY when awaiting non-blocking I/O**:
  - `await httpx_client.get(...)`
  - `await db.execute(...)` (async SQLAlchemy)
  - `await asyncio.sleep(...)`
- **Use standard `def` for CPU-bound or synchronous blocking I/O**:
  - If calling synchronous code (e.g., standard disk I/O, non-async libraries like `requests`), define the route handler as `def run_sync(...)`.
  - FastAPI will automatically run `def` handlers in an external worker threadpool (`ThreadPoolExecutor`), preventing event loop starvation.
- **NEVER call blocking code inside `async def`**: Calling `time.sleep()` or blocking socket reads inside `async def` freezes the entire server process!

## 3. Standard JSON Response Envelope
- Never return bare, ad-hoc JSON dictionaries. All endpoints must adhere to the standardized response envelope:
  ```json
  {
    "success": true,
    "statusCode": 200,
    "message": "Operation completed successfully",
    "errors": [],
    "data": { ... }
  }
  ```
- Handled errors must return the standard error envelope matching `app/core/exception_handlers.py`:
  ```json
  {
    "success": false,
    "statusCode": 403,
    "errorCode": "ERR_SCOPE_VIOLATION",
    "component": "scope_lock",
    "message": "Unauthorized file edit attempted",
    "errors": [
      {
        "field": "file_path",
        "message": "Edit blocked",
        "code": "ERR_SCOPE_VIOLATION",
        "suggestedFix": "Submit a scope expansion request."
      }
    ],
    "data": {}
  }
  ```

## 4. Pydantic v2 Best Practices
- Use `pydantic.BaseModel` with strict type annotations:
  ```python
  from pydantic import BaseModel, Field, ConfigDict

  class MissionRequest(BaseModel):
      model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

      goal: str = Field(min_length=5, max_length=2000, description="Task objective")
      max_iterations: int = Field(default=15, ge=1, le=50)
      target_files: list[str] = Field(default_factory=list)
  ```
- Use `Field(default_factory=list)` instead of mutable default arguments (`default=[]`).

## 5. Dependency Injection (`Depends`)
- Isolate database sessions, security authentication, and request contexts through injectable dependencies:
  ```python
  async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
      async with async_session_factory() as session:
          try:
              yield session
              await session.commit()
          except Exception:
              await session.rollback()
              raise
  ```
- Never create ad-hoc database connections directly inside route handler functions.

## 6. Real-Time Streaming & Server-Sent Events (SSE)
- When streaming LLM reasoning or agent event transitions, use `EventSourceResponse` from `sse_starlette.sse`:
  ```python
  @router.get("/stream/{mission_id}")
  async def stream_agent_events(mission_id: str):
      async def event_generator():
          async for event in orchestrator.execute_mission_pipeline(mission_id):
              yield {
                  "event": event.get("type", "message"),
                  "data": json.dumps(event),
              }
      return EventSourceResponse(event_generator())
  ```
