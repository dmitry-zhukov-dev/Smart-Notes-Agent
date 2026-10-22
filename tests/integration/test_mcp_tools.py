
"""Integration tests for the Smart Notes MCP server."""

import importlib.util
from pathlib import Path

import anyio
from mcp import Client


_server_path = Path(__file__).resolve().parents[2] / "mcp_server.py"
_spec = importlib.util.spec_from_file_location("mcp_server", _server_path)

if _spec is None or _spec.loader is None:
    raise ImportError(f"Cannot load MCP server from {_server_path}")

_mcp_server_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mcp_server_module)
mcp = _mcp_server_module.mcp


EXPECTED_TOOLS = {
    "list_notes",
    "read_note",
    "search_notes",
    "prepare_note_write",
    "calculator",
}


def test_mcp_tools_are_registered() -> None:
    async def check() -> None:
        async with Client(mcp) as client:
            result = await client.list_tools()
            actual_tools = {tool.name for tool in result.tools}

            assert EXPECTED_TOOLS <= actual_tools

    anyio.run(check)


def test_calculator_tool_call() -> None:
    async def check() -> None:
        async with Client(mcp) as client:
            result = await client.call_tool(
                "calculator",
                {"expression": "2 + 3 * 4"},
            )

            assert not result.is_error
            assert result.structured_content["success"] is True
            assert result.structured_content["result"] == 14

    anyio.run(check)
