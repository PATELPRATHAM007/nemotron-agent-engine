---
name: clean-architecture
category: architecture
description: Layered clean architecture, domain isolation, dependency inversion, and architectural boundary rules.
keywords: [architecture, domain, layer, dependency, service, repository, solid, isolation, boundaries]
---

# Clean Architecture & Layering Skill

## 1. Strict Layer Hierarchy & Dependency Direction
- Software systems must enforce unidirectional dependency boundaries:
  ```text
  [ Presentation Layer: Routes / Controllers / CLI ]
                      │
                      ▼
  [ Application Layer: Services / Orchestrators / Workflows ]
                      │
                      ▼
  [ Domain Core Layer: Entities / Business Invariants / Schema ]
                      │
                      ▼
  [ Infrastructure Layer: Database / Redis / External APIs / LLM ]
  ```
- **Rule of Dependency Inversion**: Higher-level policies must not depend on lower-level details; both should depend on abstractions.
- **Strict Boundary Guard (Gate 4 Rule)**:
  - Code inside `app/intelligence/` or `app/core/` must **NEVER** import from `app/modules/agent/routes` or import `fastapi.APIRouter`.
  - Domain logic must remain executable in headless test environments without web dependencies.

## 2. Interface Abstraction via Protocols
- Define abstract dependencies using Python's `typing.Protocol` or `abc.ABC`:
  ```python
  from typing import Protocol

  class CodeIndexerProtocol(Protocol):
      def parse_module(self, file_path: str) -> ParsedModule: ...
      def extract_symbols(self, file_path: str) -> list[SymbolDefinition]: ...
  ```
- Application services receive the protocol as a constructor argument rather than instantiating hardcoded concrete singletons.

## 3. Repository & Data Access Patterns
- Business logic must never compose raw SQL statements directly in service workflows.
- Encapsulate storage logic behind Repository classes:
  ```python
  class MemoryStoreRepository:
      def get_lesson(self, lesson_id: str) -> HistoricalLesson | None: ...
      def save_lesson(self, lesson: HistoricalLesson) -> None: ...
  ```

## 4. Architectural Anti-Patterns to Avoid
- **God Objects / Bloated Modules**: Avoid single files with >500 lines mixing persistence, validation, and serialization.
- **Circular Imports**: If module A needs module B and B needs A, introduce an abstract Protocol or move shared types to a neutral `schema.py`.
- **Leaky Domain Entities**: Database ORM models should not be returned directly to public API clients; always transform into dedicated response DTOs (`schemas.py`).
