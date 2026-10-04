"""
Inspect Command Handler (/inspect)
==================================
Deeply inspects files, directories, modules, or services:
line counts, directory trees, AST symbol inventories, and dependencies.
"""

import os
import time
from typing import Any, AsyncGenerator

from app.core.logging_config import get_logger
from app.modules.agent.commands.models import ParsedCommand
from app.modules.intelligence.indexing.ast_parser import parse_python_file

logger = get_logger(__name__)


class InspectCommandHandler:
    """Orchestrates /inspect deep examination."""

    @classmethod
    async def execute(
        cls,
        parsed: ParsedCommand,
        workspace_root: str,
        mission_id: str = "",
    ) -> AsyncGenerator[dict[str, Any], None]:
        start_time = time.time()
        target = parsed.query_string.strip()

        if not target:
            target = "."

        full_path = os.path.normpath(os.path.join(workspace_root, target))

        yield {
            "type": "command.started",
            "command": "/inspect",
            "mission_id": mission_id,
            "timestamp": start_time,
            "payload": {"target": target},
        }

        yield {
            "type": "token",
            "content": f"🔍 **Inspecting:** `{target}`\n\n",
        }

        if not os.path.exists(full_path):
            yield {
                "type": "token",
                "content": f"❌ Target path `{target}` does not exist in workspace.\n",
            }
            yield {
                "type": "command.failed",
                "command": "/inspect",
                "mission_id": mission_id,
                "payload": {"reason": f"Path not found: {target}"},
            }
            return

        if os.path.isfile(full_path):
            # File inspection
            classes: list[str] = []
            funcs: list[str] = []
            imports_count: int = 0
            line_count: int = 0
            stat = os.stat(full_path)
            try:
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                    line_count = len(lines)
            except Exception:
                line_count = 0

            if full_path.endswith(".py"):
                try:
                    mod = parse_python_file(full_path)
                    classes = [s.name for s in mod.symbols if getattr(s.kind, "value", str(s.kind)) == "class"]
                    funcs = [s.name for s in mod.symbols if getattr(s.kind, "value", str(s.kind)) in ("function", "method")]
                    imports_count = len(mod.imports)
                except Exception:
                    pass

            report = (
                f"### File Inspection: `{target}`\n\n"
                f"- **Size**: {stat.st_size:,} bytes\n"
                f"- **Lines of Code**: {line_count:,}\n"
                f"- **Classes ({len(classes)})**: {', '.join(classes[:8]) or 'None'}\n"
                f"- **Functions ({len(funcs)})**: {', '.join(funcs[:8]) or 'None'}\n"
                f"- **Imports**: {imports_count}\n"
            )
            yield {"type": "token", "content": report}

        elif os.path.isdir(full_path):
            # Directory inspection
            yield {"type": "command.progress", "step": "dir_inspect", "message": "Scanning directory tree and child files"}
            entries = os.listdir(full_path)
            dirs = [e for e in entries if os.path.isdir(os.path.join(full_path, e)) and not e.startswith(".")]
            files = [e for e in entries if os.path.isfile(os.path.join(full_path, e)) and not e.startswith(".")]

            report = (
                f"### Directory Inspection: `{target}/`\n\n"
                f"- **Subdirectories ({len(dirs)})**: {', '.join(sorted(dirs)[:12]) or 'None'}\n"
                f"- **Files ({len(files)})**: {', '.join(sorted(files)[:15]) or 'None'}\n"
            )
            yield {"type": "token", "content": report}

        duration = time.time() - start_time
        yield {
            "type": "command.completed",
            "command": "/inspect",
            "mission_id": mission_id,
            "duration": duration,
            "payload": {"target": target},
        }
