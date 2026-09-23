import pytest
import asyncio
from aether.tools.executor import ToolExecutor
from aether.storage.database import AsyncSessionLocal, init_db
from aether.tools.permissions import PermissionManager

@pytest.mark.asyncio
async def test_sandbox_directory_restriction():
    """
    Verify that the Rust sandbox prevents access to files outside the allowed directory.
    """
    async with AsyncSessionLocal() as session:
        await init_db()
        pm = PermissionManager(session)
        agent_id = "security_test_agent"
        await pm.grant_permission(agent_id, "shell.execute")

        executor = ToolExecutor(session)

        # Attempt to access sensitive system files
        # The sandbox must restrict access to the authorized directory.
        result = await executor.execute(
            agent_id,
            "shell.execute",
            {"command": "cat /etc/passwd"}
        )

        # Verify that sensitive content is not returned
        # Expected outcomes: 'Permission denied', 'File not found', or other access restrictions.
        assert "root:x:0:0" not in result
        assert any(msg in result for msg in ["denied", "not found", "Error", "forbidden"])

@pytest.mark.asyncio
async def test_sandbox_command_injection():
    """
    Verify that command injection attempts are handled safely.
    """
    async with AsyncSessionLocal() as session:
        await init_db()
        pm = PermissionManager(session)
        agent_id = "injection_test_agent"
        await pm.grant_permission(agent_id, "shell.execute")

        executor = ToolExecutor(session)

        # Attempt command chaining to execute unauthorized operations
        # The sandbox utilizes execvp with a list of arguments, preventing shell-style
        # chaining (;, &&, ||) unless explicitly invoked via a shell interpreter.
        result = await executor.execute(
            agent_id,
            "shell.execute",
            {"command": "ls ; cat /etc/passwd"}
        )

        # Verify the command is treated as a single literal or fails to execute the chain.
        assert "root:x:0:0" not in result
        assert any(msg in result for msg in ["not found", "Error", "failed"])

@pytest.mark.asyncio
async def test_sandbox_resource_exhaustion_attempt():
    """
    Verify that the sandbox prevents simple fork-bombs or resource exhaustion.
    """
    async with AsyncSessionLocal() as session:
        await init_db()
        pm = PermissionManager(session)
        agent_id = "stress_test_agent"
        await pm.grant_permission(agent_id, "shell.execute")

        executor = ToolExecutor(session)

        # Attempt resource exhaustion via recursive process creation (fork bomb)
        # The sandbox must enforce process limits or execution timeouts.
        result = await executor.execute(
            agent_id,
            "shell.execute",
            {"command": ":() { :|:; }; :"}
        )

        # Verify system stability and that the sandbox returned an appropriate error.
        assert any(msg in result for msg in ["Error", "failed", "killed", "timeout"])
