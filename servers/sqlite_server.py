
import sqlite3
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("sqlite-server")

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "shop.db"
MAX_ROWS = 100


def get_connection() -> sqlite3.Connection:
    """Open the database in read-only mode."""
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    # SQLite URI mode=ro prevents database writes.
    connection = sqlite3.connect(
        f"{DB_PATH.as_uri()}?mode=ro",
        uri=True,
        timeout=5,
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only = ON")
    connection.set_progress_handler(
        lambda: 1,  # Interrupt excessively long-running queries.
        1_000_000,
    )
    return connection


def validate_select(sql: str) -> str:
    """Allow one SELECT or WITH query, not SQL modifications."""
    cleaned = sql.strip()

    if not cleaned:
        raise ValueError("SQL query cannot be empty.")

    # Permit one optional trailing semicolon, but reject multiple statements.
    if cleaned.endswith(";"):
        cleaned = cleaned[:-1].rstrip()

    if ";" in cleaned:
        raise ValueError("Only one SQL statement is allowed.")

    first_word = cleaned.split(None, 1)[0].upper()

    if first_word not in {"SELECT", "WITH"}:
        raise ValueError("Only SELECT or WITH queries are allowed.")

    forbidden = {
        "INSERT", "UPDATE", "DELETE", "REPLACE",
        "CREATE", "ALTER", "DROP", "ATTACH", "DETACH",
        "PRAGMA", "VACUUM", "REINDEX",
    }

    # Conservative keyword check to reject modification keywords.
    # SQLite read-only mode remains the primary write-protection layer.
    tokens = cleaned.upper().replace("(", " ").replace(")", " ").split()
    if any(token in forbidden for token in tokens):
        raise ValueError("Query contains a prohibited SQL keyword.")

    return cleaned


@mcp.tool()
def list_tables() -> dict[str, Any]:
    """List tables available in the sample shop database."""
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()

    return {"tables": [row["name"] for row in rows]}


@mcp.tool()
def describe_table(table_name: str) -> dict[str, Any]:
    """Return column names and types for a database table."""
    if not table_name.replace("_", "").isalnum():
        raise ValueError("Invalid table name.")

    with get_connection() as connection:
        tables = {
            row["name"]
            for row in connection.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type = 'table'
                """
            ).fetchall()
        }

        if table_name not in tables:
            raise ValueError(f"Unknown table: {table_name}")

        # The name is validated above and checked against actual table names.
        columns = connection.execute(
            f'PRAGMA table_info("{table_name}")'
        ).fetchall()

    return {
        "table": table_name,
        "columns": [
            {
                "name": column["name"],
                "type": column["type"],
                "not_null": bool(column["notnull"]),
                "primary_key": bool(column["pk"]),
            }
            for column in columns
        ],
    }


@mcp.tool()
def query_database(sql: str) -> dict[str, Any]:
    """Run one read-only SELECT/WITH query, returning at most 100 rows."""
    cleaned = validate_select(sql)

    with get_connection() as connection:
        cursor = connection.execute(cleaned)
        columns = [item[0] for item in (cursor.description or [])]
        rows = cursor.fetchmany(MAX_ROWS + 1)

    truncated = len(rows) > MAX_ROWS
    rows = rows[:MAX_ROWS]

    return {
        "columns": columns,
        "rows": [dict(row) for row in rows],
        "row_count": len(rows),
        "truncated": truncated,
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
