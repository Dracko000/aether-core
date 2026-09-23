import json
import httpx
from typing import Any, Dict, Optional
from aether.tools.registry import registry
from aether.tools.permissions import PermissionManager
from sqlalchemy.ext.asyncio import AsyncSession

class ToolExecutor:
    """
    Coordinates tool selection, authorization, and execution within the cognitive architecture.
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
    Interface for interacting with the secure execution environment.
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
            # Implementation detail: Current version utilizes a TCP socket for the sandbox interface.
            # Future iterations will transition to a formal HTTP or gRPC API.
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(("127.0.0.1", 9000))
            s.sendall(json.dumps(payload).encode())
            response = s.recv(4096)
            s.close()
            return json.loads(response.decode())
