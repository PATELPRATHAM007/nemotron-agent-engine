"""
Tests for Import Resolution Engine (Phase 1)
"""

from app.intelligence.indexing.ast_parser import ImportDefinition
from app.intelligence.indexing.import_resolver import (
    ImportResolver,
    resolve_relative_module,
)


def test_resolve_relative_module():
    # level 1: current directory / package
    resolved = resolve_relative_module("app.modules.agent.engine", "tools", level=1)
    assert resolved == "app.modules.agent.tools"

    # level 2: parent package
    resolved = resolve_relative_module(
        "app.modules.agent.engine", "core.config", level=2
    )
    assert resolved == "app.modules.core.config"

    # level 3: grandparent package
    resolved = resolve_relative_module(
        "app.modules.agent.engine", "core.config", level=3
    )
    assert resolved == "app.core.config"

    # level 0: absolute
    resolved = resolve_relative_module("app.modules.agent.engine", "os.path", level=0)
    assert resolved == "os.path"


def test_import_resolver_classifies_internal_vs_external(tmp_path):
    # Create sample project structure
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    (app_dir / "__init__.py").write_text("")
    (app_dir / "service.py").write_text("def do_work(): pass")

    resolver = ImportResolver(str(tmp_path))

    # Internal import
    imp_internal = ImportDefinition(
        module="app.service", name="do_work", is_from=True, level=0
    )
    res_internal = resolver.resolve("app.main", imp_internal)
    assert res_internal.is_internal is True
    assert res_internal.resolved_module == "app.service"

    # External library import
    imp_external = ImportDefinition(
        module="fastapi", name="FastAPI", is_from=True, level=0
    )
    res_external = resolver.resolve("app.main", imp_external)
    assert res_external.is_internal is False
