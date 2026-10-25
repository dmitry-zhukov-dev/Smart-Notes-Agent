
import pytest
import os
import shutil
import uuid
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from smart_notes.agent.graph import build_graph
from tests.evaluation.test_scenarios import FakeListChatModel, setup_eval_env, calculator, list_notes, read_note, prepare_note_write

@pytest.fixture
def workspace_tmp_path():
    unique_id = str(uuid.uuid4())[:8]
    p = Path(f"C:/MyProjectsGit/Smart-Notes-Agent/pytest_eval_{unique_id}")
    p.mkdir(parents=True, exist_ok=True)
    yield p
    shutil.rmtree(p, ignore_errors=True)

def test_hitl_approval_writes_one_file(workspace_tmp_path):
    # Verify exactly one file is written on approval
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
                config = {"configurable": {"thread_id": "test_hitl"}}
                
                try:
                    await graph.ainvoke(
                        {"messages": [HumanMessage(content="Save to test.md")]},
                        config=config
                    )
                except: pass
                
                # Approve
                from langgraph.types import Command
                await graph.ainvoke(Command(resume=True), config=config)
                
                # Check results
                files = list(notes_dir.glob("*.md"))
                assert len(files) == 1
                assert files[0].name == "test.md"

    import asyncio
    asyncio.run(run())
    p1.stop()
    p2.stop()

def test_hitl_rejection_writes_no_files(workspace_tmp_path):
    # Verify no files are written on rejection
    db_path, notes_dir, p1, p2 = setup_eval_env(workspace_tmp_path)
    p1.start()
    
    async def run():
        responses = [
            AIMessage(content="", tool_calls=[{
                "name": "prepare_note_write",
                "args": {"filename": "test.md", "content": "Hello world"},
                "id": "call1"
            }]),
            AIMessage(content="Rejected.")
        ]
        model = FakeListChatModel(responses=responses)
        
        async with AsyncSqliteSaver.from_conn_string(str(db_path)) as checkpointer:
            with patch("smart_notes.agent.graph.create_llm", return_value=model):
                graph = await build_graph(checkpointer)
                config = {"configurable": {"thread_id": "test_hitl_rej"}}
                
                try:
                    await graph.ainvoke(
                        {"messages": [HumanMessage(content="Save to test.md")]},
                        config=config
                    )
                except: pass
                
                # Reject
                from langgraph.types import Command
                await graph.ainvoke(Command(resume=False), config=config)
                
                # Check results
                files = list(notes_dir.glob("*.md"))
                assert len(files) == 0

    import asyncio
    asyncio.run(run())
    p1.stop()
    p2.stop()
