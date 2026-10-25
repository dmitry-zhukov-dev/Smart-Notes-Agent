from pathlib import Path


def get_notes_dir() -> Path:
    """Return the absolute path to the notes directory."""
    project_root = Path(__file__).resolve().parents[3]
    return project_root / "data" / "notes"

def list_notes() -> list[str]:
    """Return the names of all Markdown notes."""
    notes_dir = get_notes_dir()

    if not notes_dir.exists():
        return []

    return sorted(
        path.name
        for path in notes_dir.glob("*.md")
        if path.is_file()
    )

def read_note(filename: str) -> str:
    """Read a Markdown note and return its content."""
    notes_dir = get_notes_dir().resolve()
    note_path = (notes_dir / filename).resolve()

    if not note_path.is_relative_to(notes_dir):
        raise ValueError("Note path must stay inside the notes directory")

    if not note_path.is_file():
        raise FileNotFoundError(f"Note not found: {filename}")

    if note_path.suffix.lower() != ".md":
        raise ValueError("Only Markdown notes can be read")

    return note_path.read_text(encoding="utf-8")

def write_note(filename: str, content: str) -> None:
    """Write content to a Markdown note inside the notes directory."""
    if not filename.strip():
        raise ValueError("Filename must not be empty")

    if Path(filename).name != filename or filename in {".", ".."}:
        raise ValueError("Filename must not contain directory paths")

    if Path(filename).suffix.lower() != ".md":
        raise ValueError("Only Markdown notes can be written")

    notes_dir = get_notes_dir().resolve()
    notes_dir.mkdir(parents=True, exist_ok=True)

    note_path = (notes_dir / filename).resolve()

    if not note_path.is_relative_to(notes_dir):
        raise ValueError("Note path must stay inside the notes directory")

    note_path.write_text(content, encoding="utf-8")