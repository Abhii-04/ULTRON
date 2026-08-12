import pathlib
import subprocess
from typing import Optional, Tuple

from langchain_core.tools import tool



# Project root
PROJECT_ROOT = (pathlib.Path.cwd() / "generated_project").resolve()

# Make sure the project directory exists before any tool is used.
PROJECT_ROOT.mkdir(parents=True, exist_ok=True)

IMP_FILES =[".env","credentials.json"]

# Safe path handling
def safe_path_for_project(path: str) -> pathlib.Path:
    """Resolve a relative path and keep it inside the generated project root."""
    if not isinstance(path, str):
        raise TypeError("Path must be a string")

    # Empty path means project root.
    if not path:
        path = "."
    requested_path = pathlib.Path(path)
    # Absolute paths are not allowed.
    if requested_path.is_absolute():
        raise ValueError(
            "Absolute paths are not allowed. "
            "Use a path relative to the project root."
        )

    # Resolve the path against the project root.
    resolved_path = (PROJECT_ROOT / requested_path).resolve()

    # Make sure the resolved path is still inside PROJECT_ROOT.
    try:
        resolved_path.relative_to(PROJECT_ROOT)
    except ValueError:
        raise ValueError(
            f"Path '{path}' is outside the project root. "
            f"Use a path relative to {PROJECT_ROOT}."
        )

    return resolved_path

# File tools
@tool
def write_file(path: str, content: str) -> str:
    """Write text content to a file inside the generated project root."""
    p = safe_path_for_project(path)

    # Create parent directories if they don't exist.
    p.parent.mkdir(parents=True, exist_ok=True)

    with open(p, "w", encoding="utf-8") as f:
        f.write(content)

    return f"WROTE:{p}"


@tool
def read_file(path: str) -> str:
    """Read a text file from inside the generated project root."""

    p = safe_path_for_project(path)

    if not p.exists():
        return ""

    if not p.is_file():
        return f"ERROR: {p} is not a file"

    with open(p, "r", encoding="utf-8") as f:
        return f.read()

@tool
def get_current_directory() -> str:
    """Return the generated project root path."""

    return str(PROJECT_ROOT)

@tool
def list_files(directory: str = ".") -> str:
    """List non-sensitive files under a generated project directory."""
    
    p = safe_path_for_project(directory)

    if not p.exists():
        return f"ERROR: {p} does not exist"

    if not p.is_dir():
        return f"ERROR: {p} is not a directory"
    
    files = [
        str(f.relative_to(PROJECT_ROOT))
        for f in p.glob("**/*")
        if f.is_file() and f.name not in IMP_FILES
    ]

    return "\n".join(files) if files else "No files found."

# Command execution
@tool
def run_cmd(
    cmd: str,
    cwd: Optional[str] = None,
    timeout: int = 30,
) -> Tuple[int, str, str]:
    """Run a shell command inside the generated project root."""
    if cwd:
        cwd_dir = safe_path_for_project(cwd)
    else:
        cwd_dir = PROJECT_ROOT

    if not cwd_dir.exists():
        return (
            1,
            "",
            f"ERROR: working directory does not exist: {cwd_dir}",
        )

    if not cwd_dir.is_dir():
        return (
            1,
            "",
            f"ERROR: working directory is not a directory: {cwd_dir}",
        )

    try:
        res = subprocess.run(
            cmd,
            shell=True,
            cwd=str(cwd_dir),
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        return (
            res.returncode,
            res.stdout,
            res.stderr,
        )

    except subprocess.TimeoutExpired:
        return (
            1,
            "",
            f"ERROR: command timed out after {timeout} seconds",
        )

    except Exception as e:
        return (
            1,
            "",
            f"ERROR: {type(e).__name__}: {e}",
        )

# Project initialization

def init_project_root() -> str:
    """Create the generated project root if it does not already exist."""

    PROJECT_ROOT.mkdir(parents=True, exist_ok=True)

    return str(PROJECT_ROOT)
