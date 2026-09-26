# Repository Architecture Rules

1. **Layer Separation**:
   - `app/intelligence/`: Repository understanding, AST, graph, impact, memory. MUST NOT import from `app/modules/*/routes.py`.
   - `app/modules/`: High-level business features and API presentation routes.
   - `app/core/`: Foundation services, logging, config, LLM gateway.
2. **Direction of Dependencies**:
   - Presentation (Routes) -> Business Services -> Domain Core -> Infrastructure.
3. **Task Scope Lock**:
   - Edits are strictly restricted to files registered in the active `TaskScope`.
