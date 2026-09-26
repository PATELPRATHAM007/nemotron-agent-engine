"""
Deterministic AST & Code Structure Parser
==========================================
Parses Python source code into deterministic AST representations, extracting:
  - Classes (hierarchy, bases, decorators, docstrings, line numbers)
  - Functions & Methods (sync/async, signatures, type hints, decorators)
  - API Routes (FastAPI @router.get, @app.post, paths, response models)
  - Function & Method Calls (caller -> callee invocations)
  - Module Imports (relative & absolute with aliases)
"""

import ast
import os
from typing import Any

from pydantic import BaseModel, Field

from app.intelligence.indexing.fingerprint import CodeFingerprint, fingerprint_file


class SymbolDefinition(BaseModel):
    """Normalized definition of a symbol extracted from AST."""

    id: str = Field(
        description="Unique hierarchical symbol path (e.g. module.Class.method)"
    )
    name: str = Field(description="Local symbol name")
    kind: str = Field(description="Symbol kind: class, function, method, route, model")
    file_path: str = Field(description="File containing this symbol")
    line_start: int
    line_end: int
    docstring: str | None = None
    signature: str = ""
    is_async: bool = False
    decorators: list[str] = Field(default_factory=list)
    parent_symbol: str | None = None
    calls: list[str] = Field(
        default_factory=list, description="Symbols called inside this definition"
    )
    route_info: dict[str, Any] | None = Field(
        default=None, description="FastAPI route metadata if applicable"
    )


class ImportDefinition(BaseModel):
    """Normalized representation of an imported module or symbol."""

    module: str
    name: str
    alias: str | None = None
    is_from: bool = False
    level: int = 0  # Relative import dot count: 0 for absolute, 1 for '.', 2 for '..'
    lineno: int = 1


class ParsedModule(BaseModel):
    """Complete structural representation of a parsed code file."""

    module_path: str
    file_path: str
    symbols: list[SymbolDefinition] = Field(default_factory=list)
    imports: list[ImportDefinition] = Field(default_factory=list)
    calls: list[dict[str, Any]] = Field(default_factory=list)
    fingerprint: CodeFingerprint
    is_valid_syntax: bool = True
    parse_error: str | None = None


class CodeASTVisitor(ast.NodeVisitor):
    """Custom AST visitor extracting symbols, decorators, routes, and calls."""

    def __init__(self, module_path: str, file_path: str):
        self.module_path = module_path
        self.file_path = file_path
        self.symbols: list[SymbolDefinition] = []
        self.imports: list[ImportDefinition] = []
        self.all_calls: list[dict[str, Any]] = []
        self.current_class: str | None = None
        self.current_scope_calls: list[str] = []

    def _extract_decorator_str(self, dec_node: ast.AST) -> str:
        """Convert decorator AST node to readable string."""
        try:
            return ast.unparse(dec_node)
        except (TypeError, AttributeError, ValueError):
            if isinstance(dec_node, ast.Name):
                return dec_node.id
            elif isinstance(dec_node, ast.Attribute):
                return f"{self._extract_decorator_str(dec_node.value)}.{dec_node.attr}"
            elif isinstance(dec_node, ast.Call):
                return self._extract_decorator_str(dec_node.func)
            return "decorator"

    def _detect_fastapi_route(self, decorators: list[str]) -> dict[str, Any] | None:
        """Detect if function has a FastAPI / Starlette / Flask route decorator."""
        http_methods = [
            "get",
            "post",
            "put",
            "delete",
            "patch",
            "options",
            "head",
            "api_route",
        ]
        for dec in decorators:
            dec_clean = dec.strip()
            # Match e.g. @router.get("/path"), @app.post("/path"), @v1_router.delete
            for method in http_methods:
                patterns = [f".{method}(", f".{method.upper()}("]
                for p in patterns:
                    if p in dec_clean:
                        # Extract basic path from string
                        path = "/"
                        if "(" in dec_clean and ")" in dec_clean:
                            args_part = dec_clean.split("(", 1)[1].rsplit(")", 1)[0]
                            first_arg = (
                                args_part.split(",")[0].strip().strip('"').strip("'")
                            )
                            if first_arg.startswith("/"):
                                path = first_arg
                        return {
                            "http_method": method.upper(),
                            "path": path,
                            "raw_decorator": dec_clean,
                        }
        return None

    def _format_signature(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
        """Extract function signature string with arguments and return type."""
        try:
            args_str = ast.unparse(node.args)
            ret_str = f" -> {ast.unparse(node.returns)}" if node.returns else ""
            prefix = "async def " if isinstance(node, ast.AsyncFunctionDef) else "def "
            return f"{prefix}{node.name}({args_str}){ret_str}"
        except (TypeError, AttributeError, ValueError):
            return f"def {node.name}(...)"

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imports.append(
                ImportDefinition(
                    module=alias.name,
                    name=alias.name,
                    alias=alias.asname,
                    is_from=False,
                    level=0,
                    lineno=node.lineno,
                )
            )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        mod_name = node.module or ""
        for alias in node.names:
            self.imports.append(
                ImportDefinition(
                    module=mod_name,
                    name=alias.name,
                    alias=alias.asname,
                    is_from=True,
                    level=node.level,
                    lineno=node.lineno,
                )
            )
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        class_name = node.name
        symbol_id = f"{self.module_path}.{class_name}"
        prev_class = self.current_class
        self.current_class = class_name

        decorators = [self._extract_decorator_str(d) for d in node.decorator_list]
        docstring = ast.get_docstring(node)
        bases = [ast.unparse(b) for b in node.bases] if node.bases else []
        sig = (
            f"class {class_name}({', '.join(bases)})"
            if bases
            else f"class {class_name}"
        )

        # Class symbol
        class_symbol = SymbolDefinition(
            id=symbol_id,
            name=class_name,
            kind="class",
            file_path=self.file_path,
            line_start=node.lineno,
            line_end=getattr(node, "end_lineno", node.lineno),
            docstring=docstring,
            signature=sig,
            decorators=decorators,
            parent_symbol=self.module_path,
        )
        self.symbols.append(class_symbol)

        self.generic_visit(node)
        self.current_class = prev_class

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._handle_function(node, is_async=False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._handle_function(node, is_async=True)

    def _handle_function(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef, is_async: bool
    ):
        func_name = node.name
        if self.current_class:
            symbol_id = f"{self.module_path}.{self.current_class}.{func_name}"
            kind = "method"
            parent = f"{self.module_path}.{self.current_class}"
        else:
            symbol_id = f"{self.module_path}.{func_name}"
            kind = "function"
            parent = self.module_path

        decorators = [self._extract_decorator_str(d) for d in node.decorator_list]
        docstring = ast.get_docstring(node)
        signature = self._format_signature(node)
        route_info = self._detect_fastapi_route(decorators)
        if route_info:
            kind = "route"

        # Capture calls inside this function
        saved_calls = self.current_scope_calls
        self.current_scope_calls = []

        self.generic_visit(node)

        function_calls = list(set(self.current_scope_calls))
        self.current_scope_calls = saved_calls

        symbol = SymbolDefinition(
            id=symbol_id,
            name=func_name,
            kind=kind,
            file_path=self.file_path,
            line_start=node.lineno,
            line_end=getattr(node, "end_lineno", node.lineno),
            docstring=docstring,
            signature=signature,
            is_async=is_async,
            decorators=decorators,
            parent_symbol=parent,
            calls=function_calls,
            route_info=route_info,
        )
        self.symbols.append(symbol)

    def visit_Call(self, node: ast.Call):
        callee_name = ""
        try:
            callee_name = ast.unparse(node.func)
        except (TypeError, AttributeError, ValueError):
            if isinstance(node.func, ast.Name):
                callee_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                callee_name = node.func.attr

        if callee_name:
            self.current_scope_calls.append(callee_name)
            self.all_calls.append(
                {
                    "callee": callee_name,
                    "lineno": getattr(node, "lineno", 0),
                    "scope_class": self.current_class,
                }
            )

        self.generic_visit(node)


def derive_module_path(file_path: str, root_dir: str | None = None) -> str:
    """Derive dotted Python module path from filesystem path."""
    clean_path = os.path.normpath(file_path)
    if root_dir:
        clean_root = os.path.normpath(root_dir)
        if clean_path.startswith(clean_root):
            clean_path = os.path.relpath(clean_path, clean_root)

    # Strip extension
    clean_path = clean_path.removesuffix(".py")

    # Convert separators
    parts = clean_path.replace("\\", "/").split("/")
    if parts and parts[-1] == "__init__":
        parts.pop()

    return ".".join(p for p in parts if p)


# High-performance in-memory cache keyed by (normalized_path, root_dir) -> (mtime, ParsedModule)
_PARSED_MODULE_CACHE: dict[str, tuple[float, ParsedModule]] = {}


def clear_ast_cache() -> None:
    """Clear in-memory AST parse cache for test resets or memory reclamation."""
    _PARSED_MODULE_CACHE.clear()


def parse_python_file(
    file_path: str, code: str | None = None, root_dir: str | None = None
) -> ParsedModule:
    """
    Deterministically parse a Python file into a ParsedModule structure.
    Catches and encapsulates SyntaxErrors without terminating.
    Accelerated with mtime-based in-memory caching to eliminate redundant disk I/O.
    """
    mtime: float = 0.0
    cache_key: str = ""

    if code is None:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        try:
            mtime = os.path.getmtime(file_path)
        except OSError:
            mtime = 0.0
        cache_key = f"{os.path.abspath(file_path)}::{root_dir or ''}"
        cached = _PARSED_MODULE_CACHE.get(cache_key)
        if cached is not None and cached[0] == mtime:
            return cached[1]

        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            code_str = f.read()
    else:
        code_str = code

    module_path = derive_module_path(file_path, root_dir)

    try:
        tree = ast.parse(code_str, filename=file_path)
        is_valid = True
        err_msg = None
    except SyntaxError as e:
        tree = None
        is_valid = False
        err_msg = f"SyntaxError at line {e.lineno}: {e.msg}"

    visitor = CodeASTVisitor(module_path=module_path, file_path=file_path)
    if tree:
        visitor.visit(tree)

    # Compute code fingerprint
    symbol_sigs = [s.signature for s in visitor.symbols]
    fp = fingerprint_file(
        file_path=file_path, code=code_str, tree=tree, symbol_sigs=symbol_sigs
    )

    result = ParsedModule(
        module_path=module_path,
        file_path=file_path,
        symbols=visitor.symbols,
        imports=visitor.imports,
        calls=visitor.all_calls,
        fingerprint=fp,
        is_valid_syntax=is_valid,
        parse_error=err_msg,
    )

    if code is None and cache_key:
        _PARSED_MODULE_CACHE[cache_key] = (mtime, result)

    return result
