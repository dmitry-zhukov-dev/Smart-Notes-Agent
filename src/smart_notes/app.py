
"""Command-line entry point for the Smart Notes Agent."""

import asyncio

from langchain_core.messages import HumanMessage

from smart_notes.agent.graph import build_graph


async def run_agent() -> None:
    """Run the interactive command-line agent."""

    graph = await build_graph()
    messages = []

    print("Smart Notes Agent is ready. Type 'exit' to quit.")

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if user_input.lower() in {"exit", "quit"}:
            print("Goodbye!")
            break

        if not user_input:
            continue

        messages.append(HumanMessage(content=user_input))

        try:
            result = await graph.ainvoke(
                {"messages": messages},
                config={"recursion_limit": 10},
            )
        except Exception:
            messages.pop()
            print(
                "\nAgent: I couldn't complete that request. "
                "Please try again later."
            )
            continue

        messages = result["messages"]
        final_message = messages[-1]
        content = final_message.content

        if isinstance(content, str):
            answer = content
        else:
            answer = "\n".join(
                block["text"]
                for block in content
                if isinstance(block, dict)
                and block.get("type") == "text"
                and isinstance(block.get("text"), str)
            )

        print(f"\nAgent: {answer}")

def main() -> None:
    """Start the asynchronous CLI application."""
    asyncio.run(run_agent())


if __name__ == "__main__":
    main()
