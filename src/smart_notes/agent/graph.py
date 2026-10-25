
"""Build the LangGraph workflow for the Smart Notes Agent."""

from pathlib import Path

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.types import Command

from smart_notes.agent.llm import create_llm
from smart_notes.agent.mcp_client import get_mcp_tools
from smart_notes.agent.nodes import approval_node, capture_pending_note, create_assistant_node, write_note_node
from smart_notes.agent.state import AgentState


DB_PATH = Path("data/checkpoints.sqlite")


async def build_graph(checkpointer: AsyncSqliteSaver):
    """Create and compile the agent graph."""

    tools = await get_mcp_tools()
    model = create_llm().bind_tools(tools)

    builder = StateGraph(AgentState)

    builder.add_node("assistant", create_assistant_node(model))
    builder.add_node("tools", ToolNode(tools))
    builder.add_node("capture", capture_pending_note)
    builder.add_node("approval", approval_node)
    builder.add_node("write", write_note_node)

    builder.add_edge(START, "assistant")
    builder.add_conditional_edges(
        "assistant",
        tools_condition,
        {
            "tools": "tools",
            END: END,
        },
    )
    builder.add_edge("tools", "capture")
    
    def route_after_capture(state: AgentState):
        if state.get("pending_note"):
            return "approval"
        return "assistant"

    builder.add_conditional_edges(
        "capture",
        route_after_capture,
        {
            "approval": "approval",
            "assistant": "assistant",
        },
    )

    def route_after_approval(state: AgentState):
        if state.get("approval_status") == "approved":
            return "write"
        return "assistant"

    builder.add_conditional_edges(
        "approval",
        route_after_approval,
        {
            "write": "write",
            "assistant": "assistant",
        },
    )
    builder.add_edge("write", "assistant")

    return builder.compile(checkpointer=checkpointer).with_config(
        {"recursion_limit": 10}
    )
