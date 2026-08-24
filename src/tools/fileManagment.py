from pathlib import Path

from langchain_core.tools import tool

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MAX_QUERY_WORDS = 6


def _trim_query(query: str) -> str | tuple[str, str]:
    """cut a query back to a title phrase."""

    words = query.split()
    if len(words) <= MAX_QUERY_WORDS:
        return query.strip()
    return " ".join(words[:MAX_QUERY_WORDS]), " ".join(words[MAX_QUERY_WORDS:])




def _resolve_project_path(filepath: str) -> Path:
    path = (PROJECT_ROOT / filepath).resolve()

    if not path.is_relative_to(PROJECT_ROOT):
        raise ValueError("filepath outside project")

    return path


@tool
def create_file(filepath: str) -> str:
    """Create an empty file under the project root."""
    path = _resolve_project_path(filepath)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(exist_ok=True)
    return f"Created file at {path.relative_to(PROJECT_ROOT)}"


@tool
def write_file(filepath: str, content: str) -> str:
    """Write text content to a file under the project root."""
    path = _resolve_project_path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

    return f"Wrote content to {path.relative_to(PROJECT_ROOT)}"


@tool
def read_file(filepath: str) -> str:
    """Read a UTF-8 text file under the project root."""
    path = _resolve_project_path(filepath)
    if not path.exists():
        return "file not found"

    return path.read_text(encoding="utf-8")


@tool
def delete_file(filepath: str) -> str:
    """Delete a file under the project root."""
    path = _resolve_project_path(filepath)
    if not path.exists():
        return "file does not exist"
    path.unlink()
    return f"Deleted {path.relative_to(PROJECT_ROOT)}"
