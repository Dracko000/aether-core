import httpx
from typing import Dict, Any
from aether.tools.registry import registry, ToolSchema

async def http_get(args: Dict[str, Any]) -> str:
    url = args.get("url")
    if not url:
        return "Error: 'url' argument is required"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)
            return response.text
    except Exception as e:
        return f"HTTP GET Error: {str(e)}"

def register_http_tools():
    registry.register(
        ToolSchema(
            name="http.get",
            description="Perform an HTTP GET request to retrieve content from a URL",
            parameters={"url": "string"},
            risk_level="LOW"
        ),
        http_get
    )
