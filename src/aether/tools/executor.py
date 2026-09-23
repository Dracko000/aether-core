import json
import httpx
from typing import Any, Dict, Optional
from aether.tools.registry import registry
from aether.tools.permissions import PermissionManager
from sqlalchemy.ext.asyncio import AsyncSession

class ToolExecutor:
    """
    Coordinates tool selection, permission checking, and execution.
    """
    def __init__(self, session: AsyncSession):
        self.session = session
        self.permissions = PermissionManager(session)

    async def execute(self, agent_id: str, tool_name: str, args: Dict[str, Any]) -> str:
        # 1. Check Permissions
        if not await self.permissions.check_permission(agent_id, tool_name):
            return f"Error: Permission denied for tool {tool_name}"

        # 2. Get Executor from Registry
        executor = registry.get_executor(tool_name)
        if not executor:
            return f"Error: Tool {tool_name} not found in registry"

        # 3. Execute
        try:
            return await executor(args)
        except Exception as e:
            return f"Error executing tool {tool_name}: {str(e)}"

class RustSandboxClient:
    """
    Client for communicating with the Rust-based secure sandbox.
    """
    def __init__(self, url: str = "http://127.0.0.1:9000"):
        self.url = url

    async def run_command(self, command: str, args: list[str]) -> Dict[str, Any]:
        payload = {
            "command": command,
            "args": args,
            "timeout_ms": 5000
        }
        async with httpx.AsyncClient() as client:
            # Note: Using raw TCP socket for the current sandbox.rs implementation
            # In a final version, we'd use a proper HTTP server or gRPC.
            # For the MVP, we'll use a simple TCP request.
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(("127.0.0.1", 9000))
            s.sendall(json.dumps(payload).encode())
            response = s.recv(4096)
            s.close()
            return json.loads(response.decode())
