
"""Build the LangGraph workflow for the Smart Notes Agent."""

from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from smart_notes.agent.llm import create_llm
from smart_notes.agent.mcp_client import get_mcp_tools
from smart_notes.agent.nodes import create_assistant_node
from smart_notes.agent.state import AgentState


async def build_graph():
    """Create and compile the agent graph."""

    tools = await get_mcp_tools()

    model = create_llm().bind_tools(tools)

    builder = StateGraph(AgentState)

    builder.add_node("assistant", create_assistant_node(model))
    builder.add_node("tools", ToolNode(tools))

    builder.add_edge(START, "assistant")

    builder.add_conditional_edges(
        "assistant",
        tools_condition,
        {
            "tools": "tools",
            END: END,
        },
    )

    builder.add_edge("tools", "assistant")

    return builder.compile().with_config({"recursion_limit": 10})
