
"""MCP server exposing Smart Notes Agent tools."""

from mcp.server.mcpserver import MCPServer

from smart_notes.tools.calculator import calculate
from smart_notes.tools.notes import (
    list_notes_tool,
    prepare_note_write_tool,
    read_note_tool,
    search_notes_tool,
)


mcp = MCPServer(
    "smart-notes-agent",
    version="0.1.0",
)


@mcp.tool()
def list_notes() -> dict[str, object]:
    """List all available Markdown notes."""
    return list_notes_tool()


@mcp.tool()
def read_note(filename: str) -> dict[str, object]:
    """Read a Markdown note by filename."""
    return read_note_tool(filename)


@mcp.tool()
def search_notes(query: str) -> dict[str, object]:
    """Search for text across Markdown notes."""
    return search_notes_tool(query)


@mcp.tool()
def prepare_note_write(
    filename: str,
    content: str,
) -> dict[str, object]:
    """Prepare a note creation or replacement for user approval.

    This tool does not write to disk.
    """
    return prepare_note_write_tool(filename, content)


@mcp.tool()
def calculator(expression: str) -> dict[str, object]:
    """Safely evaluate a basic mathematical expression."""
    return calculate(expression)


if __name__ == "__main__":
    mcp.run(transport="stdio")
