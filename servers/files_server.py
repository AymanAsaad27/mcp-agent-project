
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("files-server")

WORKSPACE = (
    Path(__file__).resolve().parents[1] / "workspace"
).resolve()

MAX_READ_BYTES = 100_000
MAX_WRITE_CHARS = 100_000


def resolve_workspace_path(relative_path: str) -> Path:
    """Resolve a relative path and reject paths outside the workspace."""
    if not relative_path or not relative_path.strip():
        raise ValueError("A relative file path is required.")

    supplied = Path(relative_path)

    if supplied.is_absolute():
        raise ValueError("Absolute paths are not allowed.")

    candidate = (WORKSPACE / supplied).resolve()

    try:
        candidate.relative_to(WORKSPACE)
    except ValueError:
        raise ValueError("Path is outside the permitted workspace.") from None

    return candidate


@mcp.tool()
def list_files(relative_path: str = ".") -> dict[str, Any]:
    """List files and directories inside the workspace.
        Use relative_path="." to list the workspace root.
        Do not pass an empty string for the root directory.
"""
    directory = resolve_workspace_path(relative_path)

    if not directory.exists():
        raise FileNotFoundError("Directory does not exist.")

    if not directory.is_dir():
        raise ValueError("The supplied path is not a directory.")

    items = []
    for item in sorted(directory.iterdir(), key=lambda p: p.name.lower()):
        items.append({
            "name": item.name,
            "type": "directory" if item.is_dir() else "file",
        })

    return {
        "directory": str(directory.relative_to(WORKSPACE)),
        "items": items,
    }


@mcp.tool()
def read_file(relative_path: str) -> dict[str, Any]:
    """Read a UTF-8 text file within the workspace."""
    file_path = resolve_workspace_path(relative_path)

    if not file_path.exists():
        raise FileNotFoundError("File does not exist.")

    if not file_path.is_file():
        raise ValueError("The supplied path is not a file.")

    # Avoid reading unexpectedly large files into the agent context.
    size = file_path.stat().st_size
    if size > MAX_READ_BYTES:
        raise ValueError(
            f"File exceeds the {MAX_READ_BYTES}-byte read limit."
        )

    content = file_path.read_text(encoding="utf-8")

    return {
        "path": str(file_path.relative_to(WORKSPACE)),
        "content": content,
        "characters": len(content),
    }


@mcp.tool()
def write_file(relative_path: str, content: str) -> dict[str, Any]:
    """Write UTF-8 text to a file within the workspace."""
    file_path = resolve_workspace_path(relative_path)

    if len(content) > MAX_WRITE_CHARS:
        raise ValueError(
            f"Content exceeds the {MAX_WRITE_CHARS}-character write limit."
        )

    if file_path.exists() and file_path.is_dir():
        raise ValueError("Cannot write content to a directory.")

    # Require the parent directory to exist; don't create directories implicitly.
    if not file_path.parent.exists():
        raise FileNotFoundError("Parent directory does not exist.")

    file_path.write_text(content, encoding="utf-8")

    return {
        "path": str(file_path.relative_to(WORKSPACE)),
        "characters_written": len(content),
        "success": True,
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
