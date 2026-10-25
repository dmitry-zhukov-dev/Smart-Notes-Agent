
"""Regression test for reading a note through the agent workflow."""

import asyncio

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from smart_notes.agent.graph import build_graph


def test_agent_reads_and_summarizes_example_note(tmp_path) -> None:
    async def check() -> None:
        db_path = tmp_path / "agent-test.sqlite"

        async with AsyncSqliteSaver.from_conn_string(str(db_path)) as checkpointer:
            graph = await build_graph(checkpointer)

            result = await graph.ainvoke(
                {
                    "messages": [
                        HumanMessage(
                            content="Read example.md and summarize its contents."
                        )
                    ]
                },
                config={
                    "configurable": {"thread_id": "read-note-test"},
                    "recursion_limit": 10,
                },
            )

        messages = result["messages"]
        tool_calls = [
            call
            for message in messages
            for call in getattr(message, "tool_calls", [])
        ]

        assert any(call["name"] == "read_note" for call in tool_calls)

        final_content = str(messages[-1].content)
        assert "My first note" in final_content or "test note" in final_content

    asyncio.run(check())
