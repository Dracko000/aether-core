import json
from typing import Dict, Any
from aether.tools.registry import registry, ToolSchema
from aether.tools.executor import RustSandboxClient

async def shell_execute(args: Dict[str, Any]) -> str:
    command = args.get("command")
    if not command:
        return "Error: 'command' argument is required"

    # Use the Rust Sandbox for shell execution
    sandbox = RustSandboxClient()
    try:
        # Split command into binary and args
        parts = command.split()
        result = await sandbox.run_command(parts[0], parts[1:])
        return f"STDOUT: {result['stdout']}\nSTDERR: {result['stderr']}\nExit Code: {result['exit_code']}"
    except Exception as e:
        return f"Sandbox Error: {str(e)}"

def register_shell_tools():
    registry.register(
        ToolSchema(
            name="shell.execute",
            description="Execute a shell command in the secure Rust sandbox",
            parameters={"command": "string"},
            risk_level="HIGH"
        ),
        shell_execute
    )
