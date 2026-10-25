
"""Graph nodes for the Smart Notes Agent."""

import json

from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.types import interrupt

from smart_notes.agent.prompts import SYSTEM_PROMPT
from smart_notes.agent.state import AgentState
from smart_notes.tools.notes import write_note_tool
from langchain_core.messages import ToolMessage

def write_note_node(state: AgentState) -> dict:
    """Write the approved note to disk."""
    pending_note = state.get("pending_note")
    approval_status = state.get("approval_status")

    if pending_note is None or approval_status != "approved":
        return {"pending_note": None, "approval_status": None}

    result = write_note_tool(pending_note["filename"], pending_note["content"])

    return {
        "messages": [ToolMessage(
            tool_call_id="system-write",
            name="write_note",
            content=json.dumps(result),
        )],
        "pending_note": None,
        "approval_status": None,
    }

def create_assistant_node(model: ChatGoogleGenerativeAI):
    """Create a node that asks the LLM to process the conversation."""

    async def assistant_node(state: AgentState) -> dict:
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            *state["messages"],
        ]

        response = await model.ainvoke(messages)

        return {"messages": [response]}

    return assistant_node


def _parse_tool_result(content: object) -> dict | None:
    """Parse a tool result into a dictionary."""
    if isinstance(content, dict):
        return content

    if isinstance(content, str):
        try:
            result = json.loads(content)
        except json.JSONDecodeError:
            return None

        return result if isinstance(result, dict) else None

    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and isinstance(block.get("text"), str):
                result = _parse_tool_result(block["text"])
                if result is not None:
                    return result

    return None


def capture_pending_note(state: AgentState) -> dict:
    """Extract a prepared note from the latest assistant tool-call batch."""

    for message in reversed(state["messages"]):
        if isinstance(message, AIMessage):
            break

        if (
            isinstance(message, ToolMessage)
            and message.name == "prepare_note_write"
        ):
            result = _parse_tool_result(message.content)

            if (
                result is not None
                and result.get("success") is True
                and isinstance(result.get("filename"), str)
                and isinstance(result.get("content"), str)
            ):
                return {
                    "pending_note": {
                        "filename": result["filename"],
                        "content": result["content"],
                    },
                    "approval_status": None,
                }

    return {
        "pending_note": None,
        "approval_status": None,
    }


def approval_node(state: AgentState) -> dict:
    """Pause the graph and ask the user to approve a pending note."""

    pending_note = state.get("pending_note")

    if pending_note is None:
        return {"approval_status": "rejected"}

    decision = interrupt(
        {
            "type": "note_approval",
            "filename": pending_note["filename"],
            "content": pending_note["content"],
            "message": "Do you want to save this note?",
        }
    )

    status = "approved" if decision is True else "rejected"

    return {"approval_status": status}
