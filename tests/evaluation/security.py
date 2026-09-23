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

        # Attempt to read a sensitive system file
        # The sandbox should either block the command or the command should fail
        # due to the restricted environment.
        result = await executor.execute(
            agent_id,
            "shell.execute",
            {"command": "cat /etc/passwd"}
        )

        # We expect either an error from the sandbox or a result that
        # does not contain the actual sensitive content.
        # Most secure sandboxes return a 'Permission denied' or 'File not found'
        # because the root is remapped.
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

        # Attempt command chaining to execute an unauthorized command
        # The Rust sandbox takes the command as a list of arguments to the execvp call,
        # which naturally prevents shell-style chaining (;, &&, ||) unless
        # explicitly invoked via /bin/sh.
        result = await executor.execute(
            agent_id,
            "shell.execute",
            {"command": "ls ; cat /etc/passwd"}
        )

        # The sandbox should treat "ls ; cat /etc/passwd" as a single binary name
        # or fail to execute the chain.
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

        # Attempt a simple fork bomb: :() { :|:; }; :
        # The sandbox should have a process limit or timeout.
        result = await executor.execute(
            agent_id,
            "shell.execute",
            {"command": ":() { :|:; }; :"}
        )

        # We check that the system didn't crash and the sandbox returned an error.
        assert any(msg in result for msg in ["Error", "failed", "killed", "timeout"])
