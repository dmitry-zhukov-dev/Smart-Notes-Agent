
"""Integration test for Gemini tool calling through LangChain."""

import asyncio

from langchain.agents import create_agent

from smart_notes.agent.llm import create_llm
from smart_notes.agent.mcp_client import get_mcp_tools


def test_gemini_calls_calculator_tool() -> None:
    async def check() -> None:
        tools = await get_mcp_tools()
        model = create_llm()
        agent = create_agent(model, tools)

        result = await agent.ainvoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            "Use the calculator tool to calculate 17 * 23. "
                            "Then tell me the result."
                        ),
                    }
                ]
            }
        )

        messages = result["messages"]
        tool_calls = [
            call
            for message in messages
            for call in getattr(message, "tool_calls", [])
        ]

        assert any(call["name"] == "calculator" for call in tool_calls)

        final_message = messages[-1]
        assert "391" in str(final_message.content)

    asyncio.run(check())
