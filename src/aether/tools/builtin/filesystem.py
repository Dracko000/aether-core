import os
import asyncio
from typing import Dict, Any
from aether.tools.registry import registry, ToolSchema

async def read_file(args: Dict[str, Any]) -> str:
    path = args.get("path")
    if not path:
        return "Error: 'path' argument is required"

    # Path resolution must be validated against the sandbox boundary to prevent directory traversal
    try:
        with open(path, 'r') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"

async def write_file(args: Dict[str, Any]) -> str:
    path = args.get("path")
    content = args.get("content")
    if not path or content is None:
        return "Error: 'path' and 'content' arguments are required"

    try:
        with open(path, 'w') as f:
            f.write(content)
        return f"Successfully wrote to {path}"
    except Exception as e:
        return f"Error writing file: {str(e)}"

def register_filesystem_tools():
    registry.register(
        ToolSchema(
            name="filesystem.read",
            description="Read the contents of a file from the local filesystem",
            parameters={"path": "string"},
            risk_level="LOW"
        ),
        read_file
    )
    registry.register(
        ToolSchema(
            name="filesystem.write",
            description="Write content to a file on the local filesystem",
            parameters={"path": "string", "content": "string"},
            risk_level="HIGH"
        ),
        write_file
    )
