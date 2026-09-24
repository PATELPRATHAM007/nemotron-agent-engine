"""
Unified Tool Registry for Nemotron 3 Ultra
===========================================
Defines the tool calling specifications in OpenAI function format
and dispatches execution to sandboxed tool implementations.
"""

from typing import Dict, Any, List
from app.tools.terminal import terminal_tool
from app.tools.filesystem import filesystem_tool


TOOLS_SCHEMA: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "execute_bash",
            "description": "Execute a shell command inside the sandboxed environment with stdout/stderr capture.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to execute.",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds (default: 30).",
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
            "name": "read_file",
            "description": "Read the text content of a file from the repository.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Relative or absolute path to the file.",
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
            "description": "Create or update a file with new content and return a unified git-style diff.",
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
            "name": "list_directory",
            "description": "List files and subdirectories at a specific path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "Path to the directory to inspect.",
                    },
                },
                "required": ["directory"],
            },
        },
    },
]


async def dispatch_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Execute the tool by name and return structured observations."""
    if tool_name == "execute_bash":
        return await terminal_tool.execute(
            command=arguments.get("command", ""),
            timeout=arguments.get("timeout", 30),
        )
    elif tool_name == "read_file":
        return filesystem_tool.read_file(filepath=arguments.get("filepath", ""))
    elif tool_name == "write_file":
        return filesystem_tool.write_file(
            filepath=arguments.get("filepath", ""),
            content=arguments.get("content", ""),
        )
    elif tool_name == "list_directory":
        return filesystem_tool.list_dir(directory=arguments.get("directory", "."))
    else:
        return {"success": False, "error": f"Unknown tool: {tool_name}"}
