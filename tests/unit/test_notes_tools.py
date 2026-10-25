
from smart_notes.tools import notes


def test_list_notes_tool_returns_filenames(monkeypatch):
    monkeypatch.setattr(
        notes,
        "list_notes",
        lambda: ["first.md", "second.md"],
    )

    result = notes.list_notes_tool()

    assert result == {
        "success": True,
        "notes": ["first.md", "second.md"],
        "count": 2,
    }


def test_read_note_tool_returns_content(monkeypatch):
    monkeypatch.setattr(
        notes,
        "read_note",
        lambda filename: "# Example" if filename == "example.md" else "",
    )

    result = notes.read_note_tool("example.md")

    assert result["success"] is True
    assert result["filename"] == "example.md"
    assert result["content"] == "# Example"


def test_search_notes_tool_finds_matching_lines(monkeypatch):
    monkeypatch.setattr(notes, "list_notes", lambda: ["example.md"])
    monkeypatch.setattr(
        notes,
        "read_note",
        lambda filename: "# Notes\nPython is useful.\nI like PYTHON.",
    )

    result = notes.search_notes_tool("python")

    assert result["success"] is True
    assert result["count"] == 1
    assert len(result["results"][0]["matches"]) == 2
    assert result["results"][0]["matches"][0]["line"] == 2


def test_search_notes_tool_rejects_empty_query():
    result = notes.search_notes_tool("   ")

    assert result["success"] is False
    assert result["error"] == "Search query must not be empty."


def test_prepare_note_write_tool_does_not_write_file(monkeypatch):
    write_called = False

    def unexpected_write(*args, **kwargs):
        nonlocal write_called
        write_called = True

    result = notes.prepare_note_write_tool(
        "draft.md",
        "Draft content",
    )

    assert result["success"] is True
    assert result["requires_approval"] is True
    assert result["written"] is False
    assert result["content"] == "Draft content"
    assert write_called is False


def test_prepare_note_write_tool_rejects_path_traversal():
    result = notes.prepare_note_write_tool(
        "../outside.md",
        "Unsafe content",
    )

    assert result["success"] is False
    assert "directory paths" in result["error"]


def test_prepare_note_write_tool_rejects_non_markdown_filename():
    result = notes.prepare_note_write_tool(
        "draft.txt",
        "Content",
    )

    assert result["success"] is False
    assert "Markdown" in result["error"]

def test_write_note_tool_writes_note(tmp_path, monkeypatch):
    from smart_notes.tools import notes

    written = {}

    def fake_write_note(filename, content):
        written["filename"] = filename
        written["content"] = content

    monkeypatch.setattr(notes, "write_note", fake_write_note)

    result = notes.write_note_tool("ideas.md", "My idea")

    assert result["success"] is True
    assert result["written"] is True
    assert result["filename"] == "ideas.md"
    assert written == {
        "filename": "ideas.md",
        "content": "My idea",
    }


def test_write_note_tool_handles_validation_error(monkeypatch):
    from smart_notes.tools import notes

    def fake_write_note(filename, content):
        raise ValueError("Invalid filename")

    monkeypatch.setattr(notes, "write_note", fake_write_note)

    result = notes.write_note_tool("../outside.md", "Content")

    assert result["success"] is False
    assert result["written"] is False
    assert result["error"] == "Invalid filename"


def test_write_note_tool_handles_os_error(monkeypatch):
    from smart_notes.tools import notes

    def fake_write_note(filename, content):
        raise OSError("Disk error")

    monkeypatch.setattr(notes, "write_note", fake_write_note)

    result = notes.write_note_tool("ideas.md", "Content")

    assert result["success"] is False
    assert result["written"] is False
    assert result["error"] == "Disk error"