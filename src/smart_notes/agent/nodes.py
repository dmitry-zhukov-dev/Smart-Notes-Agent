
"""Graph nodes for the Smart Notes Agent."""

from langchain_core.messages import SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from smart_notes.agent.prompts import SYSTEM_PROMPT
from smart_notes.agent.state import AgentState


def create_assistant_node(model: ChatGoogleGenerativeAI):
    """Create a node that asks the LLM to process the conversation."""

    async def assistant_node(state: AgentState) -> dict:
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            *state["messages"],
        ]

        response = await model.ainvoke(messages)

        return {"messages": [response]}

    return assistant_node
