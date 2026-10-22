
"""Tools for working with Markdown notes.

These functions form the notes-tool layer between the agent
and the note service. File-system operations remain in the service.
"""

from smart_notes.services.note_service import (
    list_notes,
    read_note,
)


def list_notes_tool() -> dict[str, object]:
    """List all available Markdown notes."""
    try:
        filenames = list_notes()
        return {
            "success": True,
            "notes": filenames,
            "count": len(filenames),
        }
    except OSError:
        return {
            "success": False,
            "error": "Could not list notes.",
        }


def read_note_tool(filename: str) -> dict[str, object]:
    """Read a Markdown note by filename."""
    try:
        content = read_note(filename)
        return {
            "success": True,
            "filename": filename,
            "content": content,
        }
    except (FileNotFoundError, ValueError) as exc:
        return {
            "success": False,
            "error": str(exc),
        }
    except OSError:
        return {
            "success": False,
            "error": "Could not read the note.",
        }


def search_notes_tool(query: str) -> dict[str, object]:
    """Search for a case-insensitive text query across Markdown notes."""
    normalized_query = query.strip()

    if not normalized_query:
        return {
            "success": False,
            "error": "Search query must not be empty.",
        }

    try:
        results = []

        for filename in list_notes():
            content = read_note(filename)
            matching_lines = [
                {
                    "line": line_number,
                    "text": line,
                }
                for line_number, line in enumerate(content.splitlines(), start=1)
                if normalized_query.casefold() in line.casefold()
            ]

            if matching_lines:
                results.append({
                    "filename": filename,
                    "matches": matching_lines,
                })

        return {
            "success": True,
            "query": normalized_query,
            "results": results,
            "count": len(results),
        }
    except (OSError, ValueError) as exc:
        return {
            "success": False,
            "error": str(exc),
        }


def prepare_note_write_tool(
    filename: str,
    content: str,
) -> dict[str, object]:
    """Prepare a note creation or replacement without writing to disk."""
    if not filename.strip():
        return {
            "success": False,
            "error": "Filename must not be empty.",
        }

    if not filename.lower().endswith(".md"):
        return {
            "success": False,
            "error": "Only Markdown filenames are allowed.",
        }

    if "/" in filename or "\\" in filename:
        return {
            "success": False,
            "error": "Filename must not contain directory paths.",
        }

    if filename in {".", ".."}:
        return {
            "success": False,
            "error": "Invalid filename.",
        }

    return {
        "success": True,
        "action": "prepare_note_write",
        "filename": filename,
        "content": content,
        "requires_approval": True,
        "written": False,
    }
