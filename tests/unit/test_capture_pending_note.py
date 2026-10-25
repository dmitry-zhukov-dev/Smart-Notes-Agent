
"""Unit tests for capturing notes prepared by the agent."""

import json

from langchain_core.messages import AIMessage, ToolMessage

from smart_notes.agent.nodes import capture_pending_note


def make_tool_messages(
    tool_name: str,
    result: dict[str, object],
) -> list:
    """Create a minimal assistant tool call and its result."""
    return [
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": tool_name,
                    "args": {},
                    "id": "call_1",
                    "type": "tool_call",
                }
            ],
        ),
        ToolMessage(
            content=json.dumps(result),
            tool_call_id="call_1",
            name=tool_name,
        ),
    ]


def test_capture_pending_note_saves_successful_preparation() -> None:
    state = {
        "messages": make_tool_messages(
            "prepare_note_write",
            {
                "success": True,
                "filename": "research.md",
                "content": "Important research notes",
                "requires_approval": True,
                "written": False,
            },
        )
    }

    result = capture_pending_note(state)

    assert result == {
        "pending_note": {
            "filename": "research.md",
            "content": "Important research notes",
        },
        "approval_status": None,
    }


def test_capture_pending_note_ignores_failed_preparation() -> None:
    state = {
        "messages": make_tool_messages(
            "prepare_note_write",
            {
                "success": False,
                "error": "Invalid filename",
            },
        )
    }

    result = capture_pending_note(state)

    assert result == {
        "pending_note": None,
        "approval_status": None,
    }


def test_capture_pending_note_ignores_other_tools() -> None:
    state = {
        "messages": make_tool_messages(
            "calculator",
            {
                "success": True,
                "filename": "research.md",
                "content": "This must not become a pending note",
            },
        )
    }

    result = capture_pending_note(state)

    assert result == {
        "pending_note": None,
        "approval_status": None,
    }
