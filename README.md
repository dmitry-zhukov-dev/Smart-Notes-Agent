# Smart Notes Agent

An educational CLI AI agent for managing local Markdown notes, built with
[LangGraph](https://github.com/langchain-ai/langgraph),
[LangChain](https://github.com/langchain-ai/langchain), and the
[Model Context Protocol (MCP)](https://github.com/modelcontextprotocol).

---

## What it does

Smart Notes Agent lets you talk to an AI assistant to read, search, and save
local Markdown notes. Every note write requires your explicit approval before
anything is saved to disk. The agent remembers your conversation across
sessions using a local SQLite database.

### What this project was built to learn

- Structuring an AI agent as a **LangGraph state machine** with conditional edges
- Exposing tools through a **local MCP server** and connecting to it with LangChain
- Implementing **human-in-the-loop (HITL)** approval using LangGraph interrupts
- Persisting agent state between sessions with a **SQLite checkpointer**
- Adding **optional observability** (Langfuse) with a configurable privacy mask

---

## Features

| Feature | Description |
|---|---|
| **List notes** | Ask the agent to list all `.md` files in `data/notes/` |
| **Read a note** | Ask the agent to read any note by filename |
| **Search notes** | Case-insensitive full-text search across all notes |
| **Calculator** | Safely evaluate arithmetic expressions (`+`, `-`, `*`, `/`, `**`, `%`) |
| **Prepare note writes** | Agent stages a note for your review — nothing is written until you approve |
| **Human approval (HITL)** | You see the filename and content and type `y` or `n` before any write |
| **Session persistence** | Conversation state is saved in `data/checkpoints.sqlite` and restored on restart |
| **Observability** | Optional Langfuse tracing with a configurable privacy mask (disabled by default) |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        app.py  (CLI loop)                       │
│   reads input → invokes graph → prints agent response           │
└────────────────────────┬────────────────────────────────────────┘
                         │  async
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              LangGraph  (graph.py / nodes.py)                   │
│                                                                 │
│  START → assistant ──(tool call?)──► tools                      │
│              ▲                          │                       │
│              │                          ▼                       │
│              │                       capture                    │
│              │                          │                       │
│              │              (pending note?)                     │
│              │                    ┌─────┘                       │
│              │                    ▼                             │
│              │                 approval  ◄── LangGraph interrupt│
│              │                    │                             │
│              │           (approved?)                            │
│              │                 ┌──┘                             │
│              │                 ▼                                │
│              └──────────── write ─────────────────── END        │
└─────────────────────────────────────────────────────────────────┘
         │                              │
   LangChain / Gemini LLM        MCP tools (mcp_server.py)
   (langchain-google-genai)      list_notes, read_note,
                                 search_notes, prepare_note_write,
                                 calculator
         │
   SQLite checkpointer
   (data/checkpoints.sqlite)
         │
   Optional: Langfuse tracing
   (langfuse callback handler)
```

**Key design points:**

- **MCP server** (`mcp_server.py`) runs as an in-process subprocess that exposes the five tools over the Model Context Protocol. LangChain connects to it via `MCPAdapter`.
- **LangGraph graph** defines the agent as a state machine. The `approval` node calls `langgraph.types.interrupt`, which pauses execution and hands control back to the CLI loop. The user types `y/n` and the graph resumes with `Command(resume=...)`.
- **SQLite checkpointer** serializes the entire `AgentState` (messages + pending note + approval status) after every step. Restarting the CLI restores the last state for the fixed thread `"smart-notes-cli"`.
- **Observability** is wired via a `CallbackHandler` passed in the LangGraph `config`. It is only created when `LANGFUSE_TRACING_ENABLED=true` and both API keys are present.

---

## Requirements

- **Python ≥ 3.14** (the project uses `str | None` syntax and newer stdlib features)
- **[uv](https://github.com/astral-sh/uv)** — dependency manager and task runner
- **Google API key** — required to run the agent (free tier available at [aistudio.google.com](https://aistudio.google.com))
- **Langfuse account** — optional; only needed if you enable tracing

---

## Setup

```powershell
# 1. Clone and enter the project
git clone <repo-url>
cd Smart-Notes-Agent

# 2. Create .env from the example template
Copy-Item .env.example .env

# 3. Open .env and set your Google API key (see Configuration below)

# 4. Install dependencies and create the virtual environment
uv sync
```

That is all. `uv sync` creates `.venv/` and installs every dependency listed in
`pyproject.toml`, including the dev dependencies (`pytest`).

---

## Configuration

Edit `.env` (never commit it — it is git-ignored).

### Required

| Variable | Description |
|---|---|
| `GOOGLE_API_KEY` | Your Google AI Studio API key. The agent will not start without this. |

### Optional — model

| Variable | Default | Description |
|---|---|---|
| `LLM_MODEL` | `gemini-2.5-flash` | Gemini model name. The `.env.example` shows `gemini-3.5-flash-lite` as an alternative. |

> **Note:** `config.py` sets the code-level default to `gemini-2.5-flash`. If you copy `.env.example` unchanged, `LLM_MODEL=gemini-3.5-flash-lite` will override that default.

### Optional — Langfuse observability

Langfuse tracing is **disabled by default**. To enable it:

1. Sign up at [cloud.langfuse.com](https://cloud.langfuse.com) (or self-host).
2. Create a project and copy the public and secret keys.
3. Set the following in your `.env`:

```dotenv
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_BASE_URL=https://cloud.langfuse.com
LANGFUSE_TRACING_ENABLED=true
```

| Variable | Default | Description |
|---|---|---|
| `LANGFUSE_TRACING_ENABLED` | `false` | Set to `true` to send traces to Langfuse. Tracing is silently skipped if either key is missing. |
| `LANGFUSE_MASK_DATA` | `false` | Set to `true` to replace all string content in traced payloads with `[MASKED]` before they leave the process. Applies to inputs, outputs, and metadata. |
| `LANGFUSE_BASE_URL` | `https://cloud.langfuse.com` | Override if you self-host Langfuse. |

> **Privacy note:** When `LANGFUSE_MASK_DATA=true`, the Langfuse SDK's `mask` hook replaces every string leaf recursively before any data is exported. Non-string values (numbers, booleans, `null`) are preserved. The agent's normal functionality is unaffected — masking only applies to the tracing export path.

---

## Running the agent

```powershell
uv run python -m smart_notes.app
```

The agent prints a prompt and waits for your input:

```
Smart Notes Agent is ready. Type 'exit' to quit.

You: list my notes
Agent: You have 1 note: example.md

You: read example.md
Agent: Here is the content of example.md: ...

You: save a note called ideas.md with content "Buy groceries"
Agent: I've prepared a note for your review.

Approval requested for ideas.md:
Content: Buy groceries
Approve? (y/n): y
Agent: The note ideas.md has been saved.

You: exit
Goodbye!
```

Type `exit` or `quit` (or press `Ctrl+C`) to stop. The conversation is saved
automatically — the next run resumes from where you left off.

Notes are stored in `data/notes/`. Only `.md` files are accepted; path
traversal attempts are rejected by the service layer.

---

## Testing

All tests are run with `uv run pytest`. The test suite does not require
Langfuse credentials (all observability calls are mocked).

### Unit tests

```powershell
# Core services and tools
uv run pytest tests/unit/test_calculator.py tests/unit/test_note_service.py tests/unit/test_notes_tools.py -v

# Agent nodes and approval flow
uv run pytest tests/unit/test_approval_node.py tests/unit/test_capture_pending_note.py -v

# Observability and privacy masking
uv run pytest tests/unit/test_observability.py tests/unit/test_privacy_masking.py -v
```

### Integration tests

```powershell
# In-process MCP server (no external services)
uv run pytest tests/integration/test_mcp_tools.py -v

# MCP stdio transport (spawns a subprocess)
uv run pytest tests/integration/test_mcp_stdio.py -v

# SQLite checkpointer round-trip (no external services)
uv run pytest tests/integration/test_persistence.py -v

# Live Gemini API calls — requires GOOGLE_API_KEY in .env
uv run pytest tests/integration/test_langchain_tools.py -v
uv run pytest tests/integration/test_agent_read_note.py -v
```

### Evaluation tests

These tests use a fake `FakeListChatModel` and do **not** require any API key:

```powershell
uv run pytest tests/evaluation/ -v
```

### Full suite

```powershell
uv run pytest -v
```

Expected result: **58 passed, 1 skipped** (see Known Limitations).

---

## Known limitations

### Skipped privacy-masking span test

`tests/unit/test_privacy_masking.py::test_mask_data_integration_with_client`
is **skipped** when run as part of the full suite, and **passes** when run
in isolation:

```powershell
uv run pytest tests/unit/test_privacy_masking.py -v   # 3 passed
uv run pytest -v                                       # 1 skipped
```

**Why:** OpenTelemetry's global `TracerProvider` is a process-level singleton.
The first Langfuse client created in a test session registers it. A second
client cannot replace it, so its `InMemorySpanExporter` receives no spans.
The test contains an intentional skip guard (`pytest.skip(...)`) to avoid
claiming masking works when the span payload cannot be observed.
This is a test isolation issue, not a bug in the application or the masking
logic — the masking itself is verified by
`tests/unit/test_observability.py::test_mask_data_integration_with_langfuse_client`,
which always runs first.

### Single fixed conversation thread

The CLI uses a single hard-coded thread ID (`"smart-notes-cli"`). All sessions
share the same conversation history. There is no built-in command to start a
fresh conversation without deleting `data/checkpoints.sqlite`.

### Windows-only verified

The project has been developed and tested on Windows (PowerShell). It should
work on macOS/Linux with minor shell adjustments (`cp` instead of `Copy-Item`,
etc.), but this has not been verified.

---

## Project structure

```
Smart-Notes-Agent/
├── src/smart_notes/
│   ├── app.py                  # CLI entry point
│   ├── config.py               # pydantic-settings configuration
│   ├── agent/
│   │   ├── graph.py            # LangGraph workflow definition
│   │   ├── nodes.py            # Graph node functions
│   │   ├── state.py            # AgentState TypedDict
│   │   ├── llm.py              # Gemini model factory
│   │   ├── mcp_client.py       # MCPAdapter connection
│   │   └── prompts.py          # System prompt
│   ├── observability/
│   │   └── __init__.py         # Langfuse callback + mask_data
│   ├── services/
│   │   └── note_service.py     # File-system operations
│   └── tools/
│       ├── calculator.py       # AST-based safe calculator
│       └── notes.py            # Tool layer (list, read, search, prepare, write)
├── mcp_server.py               # MCP server exposing the five tools
├── data/
│   ├── notes/                  # Your Markdown notes live here
│   └── checkpoints.sqlite      # Conversation state (auto-created)
├── tests/
│   ├── unit/                   # Fast, no external dependencies
│   ├── integration/            # Some require GOOGLE_API_KEY
│   └── evaluation/             # Deterministic end-to-end with fake model
├── .env.example                # Template — copy to .env and fill in keys
└── pyproject.toml              # Dependencies, build config, pytest config
```
