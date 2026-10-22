"""Regression test for reading note through the agent workflow."""

import asyncio
from langchain_core.messages import HumanMessage
from smart_notes.agent.graph import build_graph


def test_agent_reads_and_summarizes_example_note() -> None:
    async def check() -> None:
        graph = await build_graph()
        result = await graph.ainvoke(
            {
                "messages": [
                    HumanMessage(
                        content="Read example.md and summarize its contents."
                    )
                ]
            },
            config={"recursion_limit": 10},
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
