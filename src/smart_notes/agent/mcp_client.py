
"""Client for connecting LangChain to the Smart Notes MCP server."""

from pathlib import Path

from langchain_core.tools import BaseTool
from langchain.mcp import MCPAdapter


PROJECT_ROOT = Path(__file__).resolve().parents[3]
MCP_SERVER_PATH = PROJECT_ROOT / "mcp_server.py"


async def get_mcp_tools() -> list[BaseTool]:
    """Connect to the local MCP server and return its tools."""
    async with MCPAdapter(MCP_SERVER_PATH) as adapter:
        return await adapter.list_tools()
