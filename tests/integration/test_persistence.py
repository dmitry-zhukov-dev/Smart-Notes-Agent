
"""Integration tests for SQLite-backed LangGraph persistence."""

import asyncio

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph

from smart_notes.agent.state import AgentState


def test_graph_state_persists_after_reopening_database(tmp_path) -> None:
    """Restore a conversation after reopening the SQLite database."""

    async def check() -> None:
        db_path = tmp_path / "checkpoints.sqlite"
        thread_id = "persistence-test-thread"
        config = {"configurable": {"thread_id": thread_id}}

        async with AsyncSqliteSaver.from_conn_string(str(db_path)) as saver:
            builder = StateGraph(AgentState)
            builder.add_node("assistant", lambda state: {})
            builder.add_edge(START, "assistant")
            builder.add_edge("assistant", END)

            graph = builder.compile(checkpointer=saver)

            await graph.ainvoke(
                {"messages": [HumanMessage(content="Remember this message.")]},
                config=config,
            )

        async with AsyncSqliteSaver.from_conn_string(str(db_path)) as saver:
            builder = StateGraph(AgentState)
            builder.add_node("assistant", lambda state: {})
            builder.add_edge(START, "assistant")
            builder.add_edge("assistant", END)

            graph = builder.compile(checkpointer=saver)

            restored = await graph.aget_state(config)
            messages = restored.values["messages"]

            assert len(messages) == 1
            assert messages[0].content == "Remember this message."

    asyncio.run(check())
