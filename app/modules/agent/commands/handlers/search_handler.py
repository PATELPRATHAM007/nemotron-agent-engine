"""
Search Command Handler (/search)
================================
Performs hybrid search across repository: exact ripgrep text matches, symbol indices,
and Git history.
"""

import os
import time
from typing import Any, AsyncGenerator

from app.core.logging_config import get_logger
from app.modules.agent.commands.models import ParsedCommand
from app.modules.intelligence.indexing.ripgrep import ripgrep_search

logger = get_logger(__name__)


class SearchCommandHandler:
    """Orchestrates hybrid repository search."""

    @classmethod
    async def execute(
        cls,
        parsed: ParsedCommand,
        workspace_root: str,
        mission_id: str = "",
    ) -> AsyncGenerator[dict[str, Any], None]:
        start_time = time.time()
        query = parsed.query_string.strip()

        if not query:
            yield {
                "type": "command.failed",
                "command": "/search",
                "mission_id": mission_id,
                "payload": {"reason": "Missing search query. Usage: /search <query>"},
            }
            yield {
                "type": "token",
                "content": "⚠️ **Please specify a search query.**\n\nUsage: `/search <query>`\nExample: `/search JWT_SECRET` or `/search \"class ProcessRunner\"`\n",
            }
            return

        yield {
            "type": "command.started",
            "command": "/search",
            "mission_id": mission_id,
            "timestamp": start_time,
            "payload": {"query": query},
        }

        yield {
            "type": "token",
            "content": f"🔎 **Searching Repository for:** *\"{query}\"*\n\n",
        }

        yield {"type": "command.progress", "step": "ripgrep", "message": "Executing ripgrep regex engine across workspace"}
        results = ripgrep_search.search_text(
            workspace_root=workspace_root,
            query=query,
            max_results=15,
        )

        if not results:
            yield {
                "type": "token",
                "content": f"No matches found for `{query}` in workspace.\n",
            }
        else:
            yield {
                "type": "token",
                "content": f"Found **{len(results)} matches** across workspace:\n\n",
            }
            formatted_lines = []
            for r in results:
                fp = r.get("filepath", "unknown")
                ln = r.get("line_number", 0)
                snippet = r.get("line_text", "").strip()
                formatted_lines.append(f"- [`{fp}:{ln}`](file://{os.path.join(workspace_root, fp)}): `{snippet[:100]}`")

            yield {
                "type": "token",
                "content": "\n".join(formatted_lines) + "\n",
            }

        duration = time.time() - start_time
        yield {
            "type": "command.completed",
            "command": "/search",
            "mission_id": mission_id,
            "duration": duration,
            "payload": {"query": query, "results_count": len(results)},
        }
