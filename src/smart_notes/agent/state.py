"""State definition for the Smart Notes Agent graph."""

from typing import Literal, TypedDict

from langgraph.graph import MessagesState


class PendingNote(TypedDict):
    """A note waiting for user approval."""

    filename: str
    content: str


class AgentState(MessagesState):
    """Track conversation and pending note approval."""

    pending_note: PendingNote | None
    approval_status: Literal["approved", "rejected"] | None