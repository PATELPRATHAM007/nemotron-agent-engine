# PROJECT CONTEXT & AGENT DIRECTIVES

## Project Overview
- **Name**: `nemotron-agent-engine`
- **Root**: `.`
- **Files Indexed**: 510
- **Git Branch**: `main` (Clean: `False`)

## Technology Stack
- **Primary Languages**: Python
- **Frameworks**: Alembic, FastAPI, Pydantic, SQLAlchemy
- **Package Managers**: pip

## Architecture Structure
- **Frontend Subsystem**: `None detected`
- **Backend Subsystem**: `app/ (modular FastAPI architecture)`
- **Test Suite**: `tests/ (Pytest test suite)`
- **Documentation**: `docs/`
- **Scripts**: `scripts/`

## Entry Points
- **Backend_Api**: `app/main.py`
- **Test_Entry**: `pytest.ini`

## Code Quality & Import Health
- **Source Files**: 220
- **Test Files**: 34
- **Import Health**: Healthy (0 broken imports)
- **Export Health**: 1 invalid exports
- **Circular Dependencies**: 0 detected

## Configuration Manifests
- `.env.example`
- `docker-compose.yml`
- `Dockerfile`
- `pytest.ini`
- `.env (sanitized)`

## Agent Operational Directives
1. Use `/plan <goal>` before multi-file modifications.
2. Verify all patches with `/test` and `/review`.
3. Do not modify or leak sensitive credentials from `.env` or credentials storage.
4. Keep repository intelligence synchronized via `/init --refresh`.
5. Strictly adhere to Clean Architecture: Presentation → Application → Domain → Infrastructure.
