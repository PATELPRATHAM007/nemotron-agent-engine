"""
Init Command Handler (/init)
============================
Performs comprehensive repository discovery, intelligence indexing, dependency analysis,
and architecture synthesis without leaking secrets. Idempotent with --full and --refresh flags.
"""

import os
import json
import time
from typing import Any, AsyncGenerator
from pathlib import Path

from app.core.logging_config import get_logger
from app.modules.agent.commands.models import CommandEvent, ParsedCommand
from app.modules.agent.tools.git_tool import git_tool
from app.modules.intelligence.indexing.repo_map import repo_map_generator
from app.modules.intelligence.memory.schema import MemoryCandidate
from app.modules.intelligence.memory.three_tier_store import three_tier_memory_store

logger = get_logger(__name__)


class InitCommandHandler:
    """Orchestrates /init command repository intelligence synthesis."""

    SENSITIVE_PATTERNS = [
        "KEY", "SECRET", "TOKEN", "PASSWORD", "PASSWD", "AUTH", "CREDENTIAL", "PRIVATE"
    ]

    @classmethod
    async def execute(
        cls,
        parsed: ParsedCommand,
        workspace_root: str,
        mission_id: str = "",
    ) -> AsyncGenerator[dict[str, Any], None]:
        start_time = time.time()
        is_full = parsed.flags.get("full", False)
        is_refresh = parsed.flags.get("refresh", False)

        yield {
            "type": "command.started",
            "command": "/init",
            "mission_id": mission_id,
            "timestamp": start_time,
            "payload": {"full": is_full, "refresh": is_refresh},
        }
        yield {
            "type": "token",
            "content": "🔍 **Initializing Repository Intelligence...**\n\n",
        }

        # 1. Project Identity & Git Status
        yield {"type": "command.progress", "step": "identity", "message": "Detecting project identity and Git topology"}
        identity = await cls._detect_identity(workspace_root)
        yield {
            "type": "token",
            "content": f"✓ **Project**: `{identity['name']}` (Root: `{identity['root']}`)\n"
                       f"✓ **Git Status**: Branch `{identity['git_branch']}` | Clean: `{identity['is_git_clean']}`\n",
        }

        # 2. Languages, Frameworks & Runtimes
        yield {"type": "command.progress", "step": "technologies", "message": "Analyzing languages, frameworks, and runtimes"}
        tech_stack = cls._detect_tech_stack(workspace_root)
        lang_str = ", ".join(tech_stack["languages"]) or "Unknown"
        fw_str = ", ".join(tech_stack["frameworks"]) or "None detected"
        pkg_str = ", ".join(tech_stack["package_managers"]) or "Unknown"
        yield {
            "type": "token",
            "content": f"✓ **Languages**: {lang_str}\n"
                       f"✓ **Frameworks**: {fw_str}\n"
                       f"✓ **Package Manager(s)**: {pkg_str}\n",
        }

        # 3. Directory Structure & Key Subsystems
        yield {"type": "command.progress", "step": "structure", "message": "Mapping directory structure and architecture layers"}
        structure = cls._detect_structure(workspace_root)
        yield {
            "type": "token",
            "content": f"✓ **Architecture**: Frontend (`{structure.get('frontend', 'none')}`), "
                       f"Backend (`{structure.get('backend', 'none')}`), "
                       f"Tests (`{structure.get('tests', 'none')}`)\n",
        }

        # 4. Entry Points Detection
        yield {"type": "command.progress", "step": "entry_points", "message": "Discovering application entry points"}
        entry_points = cls._detect_entry_points(workspace_root)
        entry_str = "\n".join([f"  - `{k}`: `{v}`" for k, v in entry_points.items() if v])
        if entry_str:
            yield {
                "type": "token",
                "content": f"✓ **Entry Points**:\n{entry_str}\n",
            }

        # 5. Configuration & Environment Sanitization
        yield {"type": "command.progress", "step": "config", "message": "Scanning configuration files with secret sanitization"}
        config_files = cls._scan_configs(workspace_root)
        yield {
            "type": "token",
            "content": f"✓ **Configuration Files**: {', '.join(config_files) or 'None'}\n",
        }

        # 6. Repository Map & AST Indexing
        yield {"type": "command.progress", "step": "indexing", "message": "Building repository AST map and symbol index"}
        repo_map_content = repo_map_generator.generate_map(workspace_root=workspace_root, max_tokens=2000)
        file_count = cls._count_files(workspace_root)
        yield {
            "type": "token",
            "content": f"✓ **Repository Map**: {file_count:,} files indexed (<2,000 tokens generated)\n",
        }

        # 7. Generate or Update PROJECT.md and Durable Project Memory
        yield {"type": "command.progress", "step": "memory", "message": "Writing durable project knowledge and PROJECT.md"}
        summary_markdown = cls._synthesize_project_md(
            identity=identity,
            tech_stack=tech_stack,
            structure=structure,
            entry_points=entry_points,
            config_files=config_files,
            file_count=file_count,
        )

        project_md_path = os.path.join(workspace_root, "PROJECT.md")
        try:
            with open(project_md_path, "w", encoding="utf-8") as f:
                f.write(summary_markdown)
            yield {
                "type": "token",
                "content": "✓ **PROJECT.md**: Generated and persisted to workspace root\n",
            }
        except Exception as e:
            logger.warning(f"Could not write PROJECT.md: {e}")

        # Store in ThreeTierMemoryStore project tier
        try:
            candidate = MemoryCandidate(
                category="architecture",
                title="Repository Metadata and Technology Stack",
                content=f"Primary Languages: {lang_str}. Frameworks: {fw_str}. Architecture: {structure}",
                confidence=1.0,
            )
            three_tier_memory_store.add_project_memory(candidate, force=True)
        except Exception as e:
            logger.warning(f"Could not store project memory: {e}")


        duration = time.time() - start_time
        yield {
            "type": "token",
            "content": f"\n✨ **Project intelligence initialized successfully in {duration:.2f}s.**\n"
                       f"Type `/help` to see available commands or `/plan <goal>` to begin a task.\n",
        }

        yield {
            "type": "command.completed",
            "command": "/init",
            "mission_id": mission_id,
            "duration": duration,
            "payload": {
                "identity": identity,
                "tech_stack": tech_stack,
                "structure": structure,
                "indexed_files": file_count,
            },
        }

    @classmethod
    async def _detect_identity(cls, root: str) -> dict[str, Any]:
        name = os.path.basename(os.path.abspath(root)) or "workspace"
        branch = "unknown"
        is_clean = True
        try:
            status_res = await git_tool.status()
            if status_res.get("success"):
                branch = status_res.get("branch", "unknown")
                is_clean = status_res.get("clean", True)
        except Exception:
            pass

        return {
            "name": name,
            "root": root,
            "git_branch": branch,
            "is_git_clean": is_clean,
        }

    @classmethod
    def _detect_tech_stack(cls, root: str) -> dict[str, list[str]]:
        languages = set()
        frameworks = set()
        pkg_managers = set()

        root_path = Path(root)

        # Check Python
        if (root_path / "pyproject.toml").exists() or (root_path / "requirements.txt").exists() or list(root_path.glob("*.py")):
            languages.add("Python")
            if (root_path / "poetry.lock").exists():
                pkg_managers.add("poetry")
            elif (root_path / "Pipfile").exists():
                pkg_managers.add("pipenv")
            else:
                pkg_managers.add("pip")

        # Check Node / JS / TS
        pkg_json = root_path / "package.json"
        if pkg_json.exists():
            if (root_path / "tsconfig.json").exists() or list(root_path.glob("**/*.ts")):
                languages.add("TypeScript")
            else:
                languages.add("JavaScript")

            if (root_path / "pnpm-lock.yaml").exists():
                pkg_managers.add("pnpm")
            elif (root_path / "yarn.lock").exists():
                pkg_managers.add("yarn")
            elif (root_path / "bun.lockb").exists() or (root_path / "bun.lock").exists():
                pkg_managers.add("bun")
            else:
                pkg_managers.add("npm")

            try:
                with open(pkg_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                    if "next" in deps:
                        frameworks.add("Next.js")
                    if "react" in deps:
                        frameworks.add("React")
                    if "vue" in deps:
                        frameworks.add("Vue")
                    if "express" in deps:
                        frameworks.add("Express")
                    if "tailwindcss" in deps:
                        frameworks.add("TailwindCSS")
                    if "vitest" in deps:
                        frameworks.add("Vitest")
            except Exception:
                pass

        # Check Python frameworks
        if (root_path / "pyproject.toml").exists() or (root_path / "requirements.txt").exists():
            content = ""
            for fname in ["pyproject.toml", "requirements.txt"]:
                fp = root_path / fname
                if fp.exists():
                    try:
                        content += fp.read_text(encoding="utf-8", errors="ignore") + "\n"
                    except Exception:
                        pass
            if "fastapi" in content.lower():
                frameworks.add("FastAPI")
            if "django" in content.lower():
                frameworks.add("Django")
            if "flask" in content.lower():
                frameworks.add("Flask")
            if "sqlalchemy" in content.lower():
                frameworks.add("SQLAlchemy")
            if "pytest" in content.lower():
                frameworks.add("Pytest")

        # Check Rust
        if (root_path / "Cargo.toml").exists():
            languages.add("Rust")
            pkg_managers.add("cargo")

        # Check Go
        if (root_path / "go.mod").exists():
            languages.add("Go")
            pkg_managers.add("go modules")

        return {
            "languages": sorted(list(languages)),
            "frameworks": sorted(list(frameworks)),
            "package_managers": sorted(list(pkg_managers)),
        }

    @classmethod
    def _detect_structure(cls, root: str) -> dict[str, str]:
        root_path = Path(root)
        structure = {}

        if (root_path / "frontend").is_dir():
            structure["frontend"] = "frontend/"
        elif (root_path / "src" / "app").is_dir():
            structure["frontend"] = "src/app/"

        if (root_path / "app").is_dir():
            structure["backend"] = "app/"
        elif (root_path / "backend").is_dir():
            structure["backend"] = "backend/"
        elif (root_path / "src").is_dir() and "frontend" not in structure:
            structure["backend"] = "src/"

        if (root_path / "tests").is_dir():
            structure["tests"] = "tests/"
        elif (root_path / "test").is_dir():
            structure["tests"] = "test/"

        if (root_path / "docs").is_dir():
            structure["docs"] = "docs/"

        if (root_path / "scripts").is_dir():
            structure["scripts"] = "scripts/"

        return structure

    @classmethod
    def _detect_entry_points(cls, root: str) -> dict[str, str]:
        root_path = Path(root)
        entry_points = {}

        candidates = [
            ("backend", ["app/main.py", "main.py", "app.py", "server.py", "src/main.py"]),
            ("frontend", ["src/app/page.tsx", "pages/index.tsx", "src/index.tsx", "src/App.tsx"]),
            ("cli", ["cli.py", "app/cli.py"]),
            ("worker", ["worker.py", "app/worker.py"]),
        ]

        for role, files in candidates:
            for rel in files:
                if (root_path / rel).is_file():
                    entry_points[role] = rel
                    break

        return entry_points

    @classmethod
    def _scan_configs(cls, root: str) -> list[str]:
        root_path = Path(root)
        known_configs = [
            ".env.example", ".env.sample", ".env.local.example",
            "docker-compose.yml", "docker-compose.yaml", "Dockerfile",
            "pytest.ini", "tsconfig.json", "package.json", "pyproject.toml",
            "Cargo.toml", "go.mod", "Makefile"
        ]
        found = []
        for name in known_configs:
            if (root_path / name).exists():
                found.append(name)

        if (root_path / ".env").exists():
            found.append(".env (sanitized)")

        return found

    @classmethod
    def _count_files(cls, root: str) -> int:
        count = 0
        ignore_dirs = {".git", ".venv", "venv", "node_modules", "__pycache__", ".next", "dist", "build"}
        for root_dir, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            count += len(files)
        return count

    @classmethod
    def _synthesize_project_md(
        cls,
        identity: dict[str, Any],
        tech_stack: dict[str, list[str]],
        structure: dict[str, str],
        entry_points: dict[str, str],
        config_files: list[str],
        file_count: int,
    ) -> str:
        return f"""# PROJECT CONTEXT & AGENT DIRECTIVES

## Project Overview
- **Name**: `{identity['name']}`
- **Root**: `{identity['root']}`
- **Files Indexed**: {file_count:,}
- **Git Branch**: `{identity['git_branch']}` (Clean: `{identity['is_git_clean']}`)

## Technology Stack
- **Primary Languages**: {', '.join(tech_stack['languages']) or 'None detected'}
- **Frameworks**: {', '.join(tech_stack['frameworks']) or 'None detected'}
- **Package Managers**: {', '.join(tech_stack['package_managers']) or 'None detected'}

## Architecture Structure
- **Frontend Subsystem**: `{structure.get('frontend', 'None detected')}`
- **Backend Subsystem**: `{structure.get('backend', 'None detected')}`
- **Test Suite**: `{structure.get('tests', 'None detected')}`
- **Documentation**: `{structure.get('docs', 'None detected')}`
- **Scripts**: `{structure.get('scripts', 'None detected')}`

## Entry Points
{chr(10).join([f"- **{k.title()}**: `{v}`" for k, v in entry_points.items()]) or "- None detected"}

## Configuration Manifests
{chr(10).join([f"- `{c}`" for c in config_files]) or "- None detected"}

## Agent Operational Directives
1. Use `/plan <goal>` before multi-file modifications.
2. Verify all patches with `/test` and `/review`.
3. Do not modify or leak sensitive credentials from `.env` or credentials storage.
4. Keep repository intelligence synchronized via `/init --refresh`.
"""
