from unittest.mock import patch

from smart_notes.agent.nodes import approval_node


def test_approval_node_returns_rejected_without_pending_note():
    result = approval_node({"messages": []})

    assert result == {"approval_status": "rejected"}


def test_approval_node_interrupts_with_pending_note():
    pending_note = {
        "filename": "ideas.md",
        "content": "My idea",
    }

    with patch(
        "smart_notes.agent.nodes.interrupt",
        return_value=True,
    ) as mock_interrupt:
        result = approval_node(
            {
                "messages": [],
                "pending_note": pending_note,
            }
        )

    mock_interrupt.assert_called_once_with(
        {
            "type": "note_approval",
            "filename": "ideas.md",
            "content": "My idea",
            "message": "Do you want to save this note?",
        }
    )
    assert result == {"approval_status": "approved"}


def test_approval_node_handles_rejection():
    with patch(
        "smart_notes.agent.nodes.interrupt",
        return_value=False,
    ):
        result = approval_node(
            {
                "messages": [],
                "pending_note": {
                    "filename": "ideas.md",
                    "content": "My idea",
                },
            }
        )

    assert result == {"approval_status": "rejected"}