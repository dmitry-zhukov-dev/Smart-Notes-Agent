
import asyncio
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from typing import Any, List, Optional
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.outputs import ChatResult, ChatGeneration
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import Command

from smart_notes.agent.graph import build_graph
from smart_notes.tools.notes import list_notes_tool, read_note_tool, prepare_note_write_tool
from smart_notes.tools.calculator import calculate
from langchain_core.tools import tool

class FakeListChatModel(BaseChatModel):
    responses: List[BaseMessage]
    _i: int = 0

    def __init__(self, responses: List[BaseMessage], **kwargs: Any):
        super().__init__(responses=responses, **kwargs)
        self._i = 0

    def bind_tools(self, tools: Any, **kwargs: Any) -> "FakeListChatModel":
        return self

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        response = self.responses[self._i]
        self._i += 1
        generation = ChatGeneration(message=response)
        return ChatResult(generations=[generation])

    @property
    def _llm_type(self) -> str:
        return "fake-list-chat-model"

# Re-define tools as LangChain tools for the graph
@tool
def calculator(expression: str) -> str:
    """Safely evaluate a basic mathematical expression."""
    return json.dumps(calculate(expression))

@tool
def list_notes() -> str:
    """List all available Markdown notes."""
    return json.dumps(list_notes_tool())

@tool
def read_note(filename: str) -> str:
    """Read a Markdown note by filename."""
    return json.dumps(read_note_tool(filename))

@tool
def prepare_note_write(filename: str, content: str) -> str:
    """Prepare a note creation or replacement for user approval."""
    return json.dumps(prepare_note_write_tool(filename, content))

MOCK_TOOLS = [calculator, list_notes, read_note, prepare_note_write]

def setup_eval_env(tmp_path: Path):
    """Setup mocks for evaluation."""
    db_path = tmp_path / "checkpoints.sqlite"
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    
    # Mock get_notes_dir to use tmp_path
    patch_notes_dir = patch("smart_notes.services.note_service.get_notes_dir", return_value=notes_dir)
    
    # Mock get_mcp_tools to return local tool objects asynchronously
    async def mock_get_mcp_tools():
        return MOCK_TOOLS
        
    patch_tools = patch("smart_notes.agent.graph.get_mcp_tools", side_effect=mock_get_mcp_tools)
    patch_tools.start()
    
    return db_path, notes_dir, patch_notes_dir, patch_tools

import shutil
import uuid

@pytest.fixture
def workspace_tmp_path():
    unique_id = str(uuid.uuid4())[:8]
    p = Path(f"C:/MyProjectsGit/Smart-Notes-Agent/pytest_eval_{unique_id}")
    p.mkdir(parents=True, exist_ok=True)
    yield p
    # Try cleanup but ignore errors
    shutil.rmtree(p, ignore_errors=True)

def test_eval_direct_answer(workspace_tmp_path):
    db_path, notes_dir, p1, p2 = setup_eval_env(workspace_tmp_path)
    p1.start()

    async def run():
        responses = [AIMessage(content="Hello! I am your assistant.")]
        model = FakeListChatModel(responses=responses)
        
        async with AsyncSqliteSaver.from_conn_string(str(db_path)) as checkpointer:
            with patch("smart_notes.agent.graph.create_llm", return_value=model):
                graph = await build_graph(checkpointer)
                result = await graph.ainvoke(
                    {"messages": [HumanMessage(content="Hi")]},
                    config={"configurable": {"thread_id": "test1"}}
                )
                assert result["messages"][-1].content == "Hello! I am your assistant."

    asyncio.run(run())
    p1.stop()
    p2.stop()

def test_eval_calculator(workspace_tmp_path):
    db_path, notes_dir, p1, p2 = setup_eval_env(workspace_tmp_path)
    p1.start()

    async def run():
        responses = [
            AIMessage(content="", tool_calls=[{
                "name": "calculator",
                "args": {"expression": "2 + 2"},
                "id": "call1"
            }]),
            AIMessage(content="The answer is 4.")
        ]
        model = FakeListChatModel(responses=responses)
        
        async with AsyncSqliteSaver.from_conn_string(str(db_path)) as checkpointer:
            with patch("smart_notes.agent.graph.create_llm", return_value=model):
                graph = await build_graph(checkpointer)
                result = await graph.ainvoke(
                    {"messages": [HumanMessage(content="What is 2+2?")]},
                    config={"configurable": {"thread_id": "test2"}}
                )
                assert "4" in result["messages"][-1].content
                tool_messages = [m for m in result["messages"] if hasattr(m, "tool_call_id")]
                assert len(tool_messages) > 0
                assert "4" in tool_messages[0].content

    asyncio.run(run())
    p1.stop()
    p2.stop()

def test_eval_hitl_approval(workspace_tmp_path):
    db_path, notes_dir, p1, p2 = setup_eval_env(workspace_tmp_path)
    p1.start()

    async def run():
        responses = [
            AIMessage(content="", tool_calls=[{
                "name": "prepare_note_write",
                "args": {"filename": "test.md", "content": "Hello world"},
                "id": "call1"
            }]),
            AIMessage(content="Note saved.")
        ]
        model = FakeListChatModel(responses=responses)
        
        async with AsyncSqliteSaver.from_conn_string(str(db_path)) as checkpointer:
            with patch("smart_notes.agent.graph.create_llm", return_value=model):
                graph = await build_graph(checkpointer)
                config = {"configurable": {"thread_id": "test3"}}
                
                try:
                    await graph.ainvoke(
                        {"messages": [HumanMessage(content="Save 'Hello world' to test.md")]},
                        config=config
                    )
                except:
                    pass

                state = await graph.aget_state(config)
                assert state.next[0] == "approval"
                assert state.tasks[0].interrupts[0].value["filename"] == "test.md"

                result = await graph.ainvoke(
                    Command(resume=True),
                    config=config
                )
                
                assert "saved" in result["messages"][-1].content.lower()
                assert (notes_dir / "test.md").exists()
                assert (notes_dir / "test.md").read_text() == "Hello world"

    asyncio.run(run())
    p1.stop()
    p2.stop()

def test_eval_hitl_rejection(workspace_tmp_path):
    db_path, notes_dir, p1, p2 = setup_eval_env(workspace_tmp_path)
    p1.start()

    async def run():
        responses = [
            AIMessage(content="", tool_calls=[{
                "name": "prepare_note_write",
                "args": {"filename": "rejected.md", "content": "Don't save me"},
                "id": "call1"
            }]),
            AIMessage(content="Okay, I won't save it.")
        ]
        model = FakeListChatModel(responses=responses)
        
        async with AsyncSqliteSaver.from_conn_string(str(db_path)) as checkpointer:
            with patch("smart_notes.agent.graph.create_llm", return_value=model):
                graph = await build_graph(checkpointer)
                config = {"configurable": {"thread_id": "test4"}}
                
                try:
                    await graph.ainvoke(
                        {"messages": [HumanMessage(content="Save 'Don't save me' to rejected.md")]},
                        config=config
                    )
                except:
                    pass

                result = await graph.ainvoke(
                    Command(resume=False),
                    config=config
                )
                
                assert not (notes_dir / "rejected.md").exists()
                assert "won't" in result["messages"][-1].content.lower()

    asyncio.run(run())
    p1.stop()
    p2.stop()


def test_eval_note_retrieval(workspace_tmp_path):
    db_path, notes_dir, p1, p2 = setup_eval_env(workspace_tmp_path)
    p1.start()

    # Pre-create a note
    (notes_dir / "todo.md").write_text("Buy grocery", encoding="utf-8")

    async def run():
        responses = [
            AIMessage(
                content="",
                tool_calls=[{"name": "read_note", "args": {"filename": "todo.md"}, "id": "call1"}],
            ),
            AIMessage(content="Your note contains: Buy grocery"),
        ]
        model = FakeListChatModel(responses=responses)

        async with AsyncSqliteSaver.from_conn_string(str(db_path)) as checkpointer:
            with patch("smart_notes.agent.graph.create_llm", return_value=model):
                graph = await build_graph(checkpointer)
                result = await graph.ainvoke(
                    {"messages": [HumanMessage(content="Read todo.md")]},
                    config={"configurable": {"thread_id": "test5"}},
                )
                assert "buy grocery" in result["messages"][-1].content.lower()

    asyncio.run(run())
    p1.stop()
    p2.stop()


def test_eval_failed_tool_call(workspace_tmp_path):
    db_path, notes_dir, p1, p2 = setup_eval_env(workspace_tmp_path)
    p1.start()

    async def run():
        responses = [
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "read_note", "args": {"filename": "non_existent.md"}, "id": "call1"}
                ],
            ),
            AIMessage(content="I couldn't find that note."),
        ]
        model = FakeListChatModel(responses=responses)

        async with AsyncSqliteSaver.from_conn_string(str(db_path)) as checkpointer:
            with patch("smart_notes.agent.graph.create_llm", return_value=model):
                graph = await build_graph(checkpointer)
                result = await graph.ainvoke(
                    {"messages": [HumanMessage(content="Read non_existent.md")]},
                    config={"configurable": {"thread_id": "test6"}},
                )
                assert "couldn't find" in result["messages"][-1].content.lower()

    asyncio.run(run())
    p1.stop()
    p2.stop()



