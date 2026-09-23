import pytest
import asyncio
from aether.tools.registry import registry
from aether.tools.builtin.filesystem import register_filesystem_tools
from aether.tools.builtin.http import register_http_tools
from aether.tools.builtin.shell import register_shell_tools
from aether.tools.executor import ToolExecutor
from aether.storage.database import AsyncSessionLocal, init_db
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.fixture(scope="module", autouse=True)
def setup_tools():
    register_filesystem_tools()
    register_http_tools()
    register_shell_tools()

@pytest.mark.asyncio
async def test_tool_permission_denied():
    async with AsyncSessionLocal() as session:
        executor = ToolExecutor(session)
        # Verify access denial for agent without assigned permissions
        result = await executor.execute("unauthorized_agent", "filesystem.read", {"path": "test.txt"})
        assert "Permission denied" in result

@pytest.mark.asyncio
async def test_tool_execution_success():
    # Initialize session and database
    async with AsyncSessionLocal() as session:
        await init_db()
        from aether.tools.permissions import PermissionManager
        pm = PermissionManager(session)
        agent_id = "authorized_agent"
        await pm.grant_permission(agent_id, "filesystem.read")

        # Create test resource for read operation
        with open("test_read.txt", "w") as f:
            f.write("Hello Aether!")

        executor = ToolExecutor(session)
        result = await executor.execute(agent_id, "filesystem.read", {"path": "test_read.txt"})
        assert "Hello Aether!" in result

        import os
        os.remove("test_read.txt")

@pytest.mark.asyncio
async def test_tool_not_found():
    async with AsyncSessionLocal() as session:
        await init_db()
        from aether.tools.permissions import PermissionManager
        pm = PermissionManager(session)
        await pm.grant_permission("agent_001", "non_existent_tool")

        executor = ToolExecutor(session)
        result = await executor.execute("agent_001", "non_existent_tool", {})
        assert "not found in registry" in result
