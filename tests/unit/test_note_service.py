
from pathlib import Path

import pytest

from smart_notes.services import note_service


def test_get_notes_dir_returns_notes_directory():
    notes_dir = note_service.get_notes_dir()

    assert notes_dir.name == "notes"
    assert notes_dir.parent.name == "data"


def test_list_notes_returns_markdown_filenames(tmp_path, monkeypatch):
    (tmp_path / "first.md").write_text("First note", encoding="utf-8")
    (tmp_path / "second.md").write_text("Second note", encoding="utf-8")
    (tmp_path / "readme.txt").write_text("Not a Markdown note", encoding="utf-8")

    monkeypatch.setattr(note_service, "get_notes_dir", lambda: tmp_path)

    assert note_service.list_notes() == ["first.md", "second.md"]


def test_list_notes_returns_empty_list_when_directory_does_not_exist(
    tmp_path, monkeypatch
):
    missing_dir = tmp_path / "missing"

    monkeypatch.setattr(note_service, "get_notes_dir", lambda: missing_dir)

    assert note_service.list_notes() == []


def test_read_note_returns_file_content(tmp_path, monkeypatch):
    note_content = "# Test note\n\nHello, world!"
    (tmp_path / "example.md").write_text(note_content, encoding="utf-8")

    monkeypatch.setattr(note_service, "get_notes_dir", lambda: tmp_path)

    assert note_service.read_note("example.md") == note_content


def test_read_note_raises_error_for_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(note_service, "get_notes_dir", lambda: tmp_path)

    with pytest.raises(FileNotFoundError):
        note_service.read_note("missing.md")


def test_read_note_rejects_path_traversal(tmp_path, monkeypatch):
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()

    outside_file = tmp_path / "secret.md"
    outside_file.write_text("Secret", encoding="utf-8")

    monkeypatch.setattr(note_service, "get_notes_dir", lambda: notes_dir)

    with pytest.raises(ValueError, match="inside the notes directory"):
        note_service.read_note("../secret.md")


def test_read_note_rejects_non_markdown_files(tmp_path, monkeypatch):
    (tmp_path / "notes.txt").write_text("Text file", encoding="utf-8")

    monkeypatch.setattr(note_service, "get_notes_dir", lambda: tmp_path)

    with pytest.raises(ValueError, match="Only Markdown"):
        note_service.read_note("notes.txt")

def test_write_note_creates_file_with_content(tmp_path, monkeypatch):
    from smart_notes.services import note_service

    notes_dir = tmp_path / "notes"
    monkeypatch.setattr(note_service, "get_notes_dir", lambda: notes_dir)

    note_service.write_note("ideas.md", "My new idea")

    assert (notes_dir / "ideas.md").read_text(encoding="utf-8") == "My new idea"


def test_write_note_rejects_path_traversal(tmp_path, monkeypatch):
    from smart_notes.services import note_service

    notes_dir = tmp_path / "notes"
    monkeypatch.setattr(note_service, "get_notes_dir", lambda: notes_dir)

    with pytest.raises(ValueError):
        note_service.write_note("../outside.md", "Should not be written")

    assert not (tmp_path / "outside.md").exists()


def test_write_note_rejects_non_markdown_file(tmp_path, monkeypatch):
    from smart_notes.services import note_service

    notes_dir = tmp_path / "notes"
    monkeypatch.setattr(note_service, "get_notes_dir", lambda: notes_dir)

    with pytest.raises(ValueError):
        note_service.write_note("notes.txt", "Should not be written")

    assert not (notes_dir / "notes.txt").exists()