
"""Integration tests for the MCP stdio transport."""

import os
import sys
from pathlib import Path

import anyio
from mcp import Client, StdioServerParameters


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SERVER_PATH = PROJECT_ROOT / "mcp_server.py"

EXPECTED_TOOLS = {
    "list_notes",
    "read_note",
    "search_notes",
    "prepare_note_write",
    "calculator",
}


def test_mcp_stdio_transport() -> None:
    async def check() -> None:
        python_path = os.pathsep.join(
            [
                str(PROJECT_ROOT),
                str(PROJECT_ROOT / "src"),
            ]
        )

        server = StdioServerParameters(
            command=sys.executable,
            args=[str(SERVER_PATH)],
            env={"PYTHONPATH": python_path},
        )

        async with Client(server) as client:
            tools_result = await client.list_tools()
            actual_tools = {tool.name for tool in tools_result.tools}

            assert EXPECTED_TOOLS <= actual_tools

            result = await client.call_tool(
                "calculator",
                {"expression": "2 + 3 * 4"},
            )

            assert not result.is_error
            assert result.structured_content["success"] is True
            assert result.structured_content["result"] == 14

    anyio.run(check)
