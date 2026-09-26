"""
Filesystem & Code Diff Tool for Nemotron 3 Ultra Agents
"""

import difflib
import os
from typing import Any


class FilesystemTool:
    """Provides file read, write, directory listing, and git-style unified diff generation."""

    def read_file(self, filepath: str) -> dict[str, Any]:
        if not os.path.exists(filepath):
            return {"success": False, "error": f"File not found: {filepath}"}
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            return {"success": True, "filepath": filepath, "content": content}
        except OSError as e:
            return {"success": False, "error": str(e)}

    def write_file(self, filepath: str, content: str) -> dict[str, Any]:
        try:
            os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
            old_content = ""
            if os.path.exists(filepath):
                with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                    old_content = f.read()

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

            # Generate unified diff
            diff = "".join(
                difflib.unified_diff(
                    old_content.splitlines(keepends=True),
                    content.splitlines(keepends=True),
                    fromfile=f"a/{os.path.basename(filepath)}",
                    tofile=f"b/{os.path.basename(filepath)}",
                )
            )

            return {
                "success": True,
                "filepath": filepath,
                "bytes_written": len(content.encode("utf-8")),
                "diff": diff,
            }
        except OSError as e:
            return {"success": False, "error": str(e)}

    def list_dir(self, directory: str) -> dict[str, Any]:
        if not os.path.exists(directory):
            return {"success": False, "error": f"Directory not found: {directory}"}
        try:
            entries: list[dict[str, Any]] = []
            for item in os.listdir(directory):
                full_path = os.path.join(directory, item)
                entries.append(
                    {
                        "name": item,
                        "is_dir": os.path.isdir(full_path),
                        "size": os.path.getsize(full_path)
                        if os.path.isfile(full_path)
                        else 0,
                    }
                )
            return {"success": True, "directory": directory, "entries": entries}
        except OSError as e:
            return {"success": False, "error": str(e)}


filesystem_tool = FilesystemTool()
