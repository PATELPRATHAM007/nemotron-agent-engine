"""
Tests for Deterministic AST Parsing and Symbol Extraction (Phase 1)
"""

from app.intelligence.indexing.ast_parser import derive_module_path, parse_python_file

SAMPLE_FASTAPI_CODE = '''"""Sample Auth Module Docstring."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    """User login payload."""
    username: str
    password: str


class AuthService:
    """Core authentication logic service."""

    def __init__(self, secret: str):
        self.secret = secret

    async def authenticate_user(self, username: str, password: str) -> Optional[dict]:
        """Authenticate user against database."""
        if username == "admin":
            return {"user_id": 1, "role": "admin"}
        return None


@router.post("/login", response_model=dict)
async def login_endpoint(payload: LoginRequest, service: AuthService = Depends()):
    """Authenticate and issue access token."""
    user = await service.authenticate_user(payload.username, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"token": "sample_jwt_token"}
'''

SAMPLE_SYNTAX_ERROR_CODE = """def broken_function(
    print("missing closing paren and colon"
"""


def test_ast_parser_extracts_classes_and_methods():
    parsed = parse_python_file("sample/auth/service.py", code=SAMPLE_FASTAPI_CODE)

    assert parsed.is_valid_syntax is True
    assert parsed.parse_error is None

    # Check class extraction
    classes = [s for s in parsed.symbols if s.kind == "class"]
    assert len(classes) == 2
    class_names = [c.name for c in classes]
    assert "LoginRequest" in class_names
    assert "AuthService" in class_names

    # Check AuthService methods
    methods = [s for s in parsed.symbols if s.kind == "method"]
    assert len(methods) == 2
    method_names = [m.name for m in methods]
    assert "__init__" in method_names
    assert "authenticate_user" in method_names

    auth_method = next(m for m in methods if m.name == "authenticate_user")
    assert auth_method.is_async is True
    assert "async def authenticate_user" in auth_method.signature
    assert "Authenticate user against database." in (auth_method.docstring or "")
    assert auth_method.parent_symbol == "sample.auth.service.AuthService"


def test_ast_parser_detects_routes():
    parsed = parse_python_file("sample/auth/router.py", code=SAMPLE_FASTAPI_CODE)

    routes = [s for s in parsed.symbols if s.kind == "route"]
    assert len(routes) == 1

    route = routes[0]
    assert route.name == "login_endpoint"
    assert route.route_info is not None
    assert route.route_info["http_method"] == "POST"
    assert route.route_info["path"] == "/login"


def test_ast_parser_extracts_calls():
    parsed = parse_python_file("sample/auth/router.py", code=SAMPLE_FASTAPI_CODE)

    route_symbol = next(s for s in parsed.symbols if s.name == "login_endpoint")
    # Calls should include service.authenticate_user and HTTPException
    callees = route_symbol.calls
    assert any("authenticate_user" in c for c in callees)
    assert any("HTTPException" in c for c in callees)


def test_ast_parser_extracts_imports():
    parsed = parse_python_file("sample/auth/router.py", code=SAMPLE_FASTAPI_CODE)

    assert len(parsed.imports) >= 3
    imported_names = [i.name for i in parsed.imports]
    assert "APIRouter" in imported_names
    assert "BaseModel" in imported_names
    assert "Optional" in imported_names


def test_ast_parser_handles_syntax_errors_gracefully():
    parsed = parse_python_file("broken.py", code=SAMPLE_SYNTAX_ERROR_CODE)

    assert parsed.is_valid_syntax is False
    assert parsed.parse_error is not None
    assert "SyntaxError" in parsed.parse_error
    assert len(parsed.symbols) == 0


def test_derive_module_path():
    assert (
        derive_module_path("app/modules/agent/engine.py") == "app.modules.agent.engine"
    )
    assert derive_module_path("app/modules/agent/__init__.py") == "app.modules.agent"
    assert derive_module_path("infra/download.py") == "infra.download"
