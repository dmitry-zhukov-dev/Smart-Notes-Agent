
"""Command-line entry point for the Smart Notes Agent."""

import asyncio
from pathlib import Path

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import Command

from smart_notes.agent.graph import build_graph
from smart_notes.observability import get_langfuse_callback


DB_PATH = Path("data/checkpoints.sqlite")
THREAD_ID = "smart-notes-cli"


async def run_agent() -> None:
    """Run the interactive CLI agent with persistent conversation state."""

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    async with AsyncSqliteSaver.from_conn_string(str(DB_PATH)) as checkpointer:
        graph = await build_graph(checkpointer)
        langfuse_callback = get_langfuse_callback()
        
        config = {
            "configurable": {"thread_id": THREAD_ID},
            "recursion_limit": 10,
        }
        
        if langfuse_callback:
            config["callbacks"] = [langfuse_callback]

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

            try:
                # Initial request
                result = await graph.ainvoke(
                    {"messages": [HumanMessage(content=user_input)]},
                    config=config,
                )
            except Exception as e:
                # Handle potential interrupts or errors
                if hasattr(e, "task"):
                    interrupt_info = e.task.interrupts[0].value
                    if isinstance(interrupt_info, dict) and interrupt_info.get("type") == "note_approval":
                        print(f"\nApproval requested for {interrupt_info['filename']}:")
                        print(f"Content: {interrupt_info['content']}")
                        choice = input("Approve? (y/n): ").strip().lower()
                        approved = choice == "y"
                        
                        # Resume graph
                        result = await graph.ainvoke(
                            Command(resume=approved),
                            config=config,
                        )
                    else:
                        print(f"\nAgent: Unexpected interruption.")
                        continue
                else:
                    print(
                        f"\nAgent: I couldn't complete that request. ({e})"
                    )
                    continue

            final_message = result["messages"][-1]
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
