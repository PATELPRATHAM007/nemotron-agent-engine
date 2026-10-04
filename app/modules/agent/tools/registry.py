"""
Standardized MCP-Compatible Tool Registry for Nemotron 3 Ultra
==============================================================
Exposes tools in standardized OpenAI Function / Model Context Protocol (MCP) schemas
and dispatches execution to sandboxed, concurrency-safe implementations:
  - Filesystem (read_file, write_file, edit_file, list_dir)
  - Subprocess Runner (execute_bash)
  - Native Git (git_status, git_diff, git_log, git_blame, git_checkpoint, git_rollback)
"""

import os
from typing import Any

from app.modules.agent.tools.browser_tool import browser_tool
from app.modules.agent.tools.git_tool import git_tool
from app.modules.agent.tools.patcher import DiffPatcher
from app.modules.agent.tools.process_runner import ProcessRunner
from app.modules.agent.tools.workspace import workspace_sandbox
from app.modules.intelligence.indexing.git_history import git_history_retriever
from app.modules.intelligence.indexing.repo_map import repo_map_generator
from app.modules.intelligence.indexing.ripgrep import ripgrep_search
from app.modules.missions.permissions import (
    PermissionDecision,
    mission_permissions,
)

TOOLS_SCHEMA: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the text content of a file from the repository with path safety.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Relative path to the file inside workspace.",
                    },
                },
                "required": ["filepath"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create a new file or completely overwrite an existing file. For modifications to existing code, prefer 'edit_file'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Target path of the file to write.",
                    },
                    "content": {
                        "type": "string",
                        "description": "The complete new content of the file.",
                    },
                },
                "required": ["filepath", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Apply a surgical, minimal hunk replacement to an existing file. Replaces target_snippet with replacement_snippet without rewriting the whole file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Path to the file to edit.",
                    },
                    "target_snippet": {
                        "type": "string",
                        "description": "Exact text snippet in the file to be replaced.",
                    },
                    "replacement_snippet": {
                        "type": "string",
                        "description": "New replacement code to substitute in place of target_snippet.",
                    },
                },
                "required": ["filepath", "target_snippet", "replacement_snippet"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List files and subdirectories at a specific workspace path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "Path to directory to inspect (default: '.').",
                        "default": ".",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "execute_bash",
            "description": "Execute a shell command inside the sandboxed workspace environment with output capture and timeout.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to execute.",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds (default: 30, max: 300).",
                        "default": 30,
                    },
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_status",
            "description": "Inspect Git working tree status (uncommitted, staged, and untracked files).",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_diff",
            "description": "Return git unified diff of current uncommitted changes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Optional specific file to limit the diff to.",
                    },
                    "staged": {
                        "type": "boolean",
                        "description": "If true, show staged changes instead of unstaged.",
                        "default": False,
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_checkpoint",
            "description": "Create a lightweight safety checkpoint of current repository state before applying risky edits.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Identifier for the checkpoint (e.g. 'pre_refactor').",
                    },
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_rollback",
            "description": "Revert uncommitted modifications in the working tree back to a clean state.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the checkpoint to roll back to.",
                    },
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ripgrep_search",
            "description": "High-speed exact text or regex search across workspace source files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Text query or regex pattern to search.",
                    },
                    "file_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional file extensions to restrict search (e.g. ['py', 'ts']).",
                    },
                    "path_filter": {
                        "type": "string",
                        "description": "Subdirectory to restrict search (e.g. 'app/modules/agent').",
                    },
                    "is_regex": {
                        "type": "boolean",
                        "description": "Whether query is a regex pattern.",
                        "default": False,
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_repo_map",
            "description": "Generate an ultra-compact architectural outline of the repository showing key classes, functions, and routes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "max_tokens": {
                        "type": "integer",
                        "description": "Maximum token budget for the map (default: 2000).",
                        "default": 2000,
                    },
                    "target_dir": {
                        "type": "string",
                        "description": "Optional subdirectory to focus the map on.",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_git_history",
            "description": "Retrieve recent commit messages and historical edits touching a specific file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Path to file to inspect commit history for.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of recent commits (default: 5).",
                        "default": 5,
                    },
                },
                "required": ["filepath"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_open",
            "description": "Navigate the headless browser to a specific URL for visual verification.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to navigate to (e.g. 'http://localhost:3000').",
                    },
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_screenshot",
            "description": "Capture a screenshot PNG of the current browser page for visual review.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Optional filename for the screenshot.",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_click",
            "description": "Click an interactive element on the page using a CSS selector.",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {
                        "type": "string",
                        "description": "CSS selector to click.",
                    },
                },
                "required": ["selector"],
            },
        },
    },
]



async def dispatch_tool(
    tool_name: str,
    arguments: dict[str, Any],
    mission_id: str | None = None,
) -> dict[str, Any]:
    """Execute the requested tool safely and return structured observations."""

    # 1. File Reading
    if tool_name == "read_file":
        filepath = arguments.get("filepath", "")
        try:
            content = workspace_sandbox.read_text(filepath)
            return {
                "success": True,
                "filepath": filepath,
                "content": content,
                "line_count": len(content.splitlines()),
            }
        except Exception as e:
            return {"success": False, "filepath": filepath, "error": str(e)}

    # 2. File Writing (Full replacement)
    elif tool_name == "write_file":
        filepath = arguments.get("filepath", "")
        content = arguments.get("content", "")
        try:
            bytes_written = workspace_sandbox.write_text(filepath, content)
            patcher = DiffPatcher(sandbox=workspace_sandbox)
            diff = patcher.preview_diff(filepath, content)
            return {
                "success": True,
                "filepath": filepath,
                "bytes_written": bytes_written,
                "diff": diff,
            }
        except Exception as e:
            return {"success": False, "filepath": filepath, "error": str(e)}

    # 3. Surgical Hunk Editing (Diff-aware)
    elif tool_name == "edit_file":
        filepath = arguments.get("filepath", "")
        target = arguments.get("target_snippet", "")
        replacement = arguments.get("replacement_snippet", "")
        patcher = DiffPatcher(sandbox=workspace_sandbox)
        res = patcher.edit_file(
            filepath=filepath,
            target_snippet=target,
            replacement_snippet=replacement,
        )
        return {
            "success": res.success,
            "filepath": res.filepath,
            "diff": res.diff,
            "replacements_made": res.replacements_made,
            "error": res.error,
        }

    # 4. Directory Listing
    elif tool_name in ("list_directory", "list_dir"):
        dirpath = arguments.get("directory", ".")
        try:
            abs_dir = workspace_sandbox.resolve_path(dirpath)
            items = []
            for entry in os.listdir(abs_dir):
                full_entry = os.path.join(abs_dir, entry)
                items.append({
                    "name": entry,
                    "is_dir": os.path.isdir(full_entry),
                    "size": os.path.getsize(full_entry) if os.path.isfile(full_entry) else 0,
                })
            return {"success": True, "directory": dirpath, "items": items}
        except Exception as e:
            return {"success": False, "directory": dirpath, "error": str(e)}

    # 5. Shell Execution with Permission Inspection
    elif tool_name == "execute_bash":
        command = arguments.get("command", "")
        timeout = arguments.get("timeout", 30)

        # Risk check via permission engine
        m_id = mission_id or "adhoc"
        eval_res = mission_permissions.evaluate_command(
            m_id, command, reason="Tool execution dispatch"
        )
        if eval_res["decision"] == PermissionDecision.DENY.value:
            return {
                "success": False,
                "exit_code": 1,
                "stdout": "",
                "stderr": f"🛑 Execution blocked: Command is prohibited by repository security policy (Risk: {eval_res['risk_level']}).",
            }
        if eval_res["decision"] == PermissionDecision.ASK.value:
            return {
                "success": False,
                "exit_code": 1,
                "stdout": "",
                "stderr": f"⚠️ Execution requires explicit human permission (Risk: {eval_res['risk_level']}).",
            }

        runner = ProcessRunner(sandbox=workspace_sandbox)
        res = await runner.run(command=command, timeout=timeout)
        return {
            "success": res.success,
            "exit_code": res.exit_code,
            "stdout": res.stdout,
            "stderr": res.stderr,
            "duration_ms": res.duration_ms,
            "timed_out": res.timed_out,
        }

    # 6. Git Operations
    elif tool_name == "git_status":
        status = git_tool.get_status()
        return {
            "success": status.is_repo,
            "branch": status.branch,
            "is_clean": status.is_clean,
            "modified": status.modified_files,
            "staged": status.staged_files,
            "untracked": status.untracked_files,
            "summary": status.summary,
        }

    elif tool_name == "git_diff":
        diff = git_tool.get_diff(
            filepath=arguments.get("filepath"),
            staged=arguments.get("staged", False),
        )
        return {"success": True, "diff": diff}

    elif tool_name == "git_log":
        logs = git_tool.get_log(
            limit=arguments.get("limit", 5),
            filepath=arguments.get("filepath"),
        )
        return {"success": True, "commits": logs}

    elif tool_name == "git_blame":
        filepath = arguments.get("filepath", "")
        blame_text = git_tool.get_blame(
            filepath=filepath,
            line_start=arguments.get("line_start"),
            line_end=arguments.get("line_end"),
        )
        return {"success": True, "filepath": filepath, "blame": blame_text}

    elif tool_name == "git_checkpoint":
        name = arguments.get("name", "checkpoint")
        cp = git_tool.create_checkpoint(name)
        return cp

    elif tool_name == "git_rollback":
        name = arguments.get("name", "checkpoint")
        rb = git_tool.rollback(name)
        return rb

    # 7. Multi-Mode Repository Intelligence (Phase 2)
    elif tool_name == "ripgrep_search":
        query = arguments.get("query", "")
        res = ripgrep_search.search(
            query=query,
            path_filter=arguments.get("path_filter"),
            file_types=arguments.get("file_types"),
            is_regex=arguments.get("is_regex", False),
        )
        return {
            "success": res.success,
            "query": res.query,
            "total_matches": res.total_matches,
            "matches": [
                {
                    "filepath": m.filepath,
                    "line": m.line_number,
                    "snippet": m.match_snippet,
                }
                for m in res.matches
            ],
            "truncated": res.truncated,
            "error": res.error,
        }

    elif tool_name == "get_repo_map":
        max_tokens = arguments.get("max_tokens", 2000)
        target_dir = arguments.get("target_dir")
        map_text = repo_map_generator.generate_map(
            max_tokens=max_tokens, target_dir=target_dir
        )
        return {
            "success": True,
            "repo_map": map_text,
            "estimated_tokens": len(map_text) // 4,
        }

    elif tool_name == "get_git_history":
        filepath = arguments.get("filepath", "")
        limit = arguments.get("limit", 5)
        history = git_history_retriever.get_recent_file_history(
            filepath=filepath, limit=limit
        )
        return {
            "success": True,
            "filepath": filepath,
            "commits": [
                {
                    "hash": c.commit_hash[:8],
                    "author": c.author,
                    "date": c.relative_date,
                    "message": c.message,
                }
                for c in history
            ],
        }

    elif tool_name == "browser_open":
        url = arguments.get("url", "")
        return await browser_tool.open(url)

    elif tool_name == "browser_screenshot":
        filename = arguments.get("filename")
        return await browser_tool.screenshot(filename)

    elif tool_name == "browser_click":
        selector = arguments.get("selector", "")
        return await browser_tool.click(selector)

    else:
        return {"success": False, "error": f"Unknown tool: '{tool_name}'"}

