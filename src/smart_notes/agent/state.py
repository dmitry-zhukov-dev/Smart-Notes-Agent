
"""State definition for the Smart Notes Agent graph."""

from langgraph.graph import MessagesState


class AgentState(MessagesState):
    """Track messages exchanged during one agent execution."""
