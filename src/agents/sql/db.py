import sqlite3
from pathlib import Path
from typing import Any

READ_ONLY_PREFIXES = ("SELECT", "WITH")
FORBIDDEN_TOKENS = (
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "TRUNCATE",
    "CREATE",
    "REPLACE",
    "ATTACH",
    "DETACH",
    "VACUUM",
    "PRAGMA",
)


def resolve_db_path(db_path: str | Path) -> Path:
    path = Path(db_path)
    if not path.exists():
        raise ValueError(f"Database path does not exist: {path}")
    if not path.is_file():
        raise ValueError(f"Database path is not a file: {path}")
    return path


def ensure_db_file(db_path: str | Path) -> Path:
    path = Path(db_path)
    if path.exists():
        if not path.is_file():
            raise ValueError(f"Database path is not a file: {path}")
        return path

    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path):
        pass
    return path


def list_tables(db_path: str | Path) -> list[str]:
    path = resolve_db_path(db_path)
    with sqlite3.connect(path) as conn:
        rows = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()
    return [str(row[0]) for row in rows]


def get_schema(db_path: str | Path, table_names: list[str]) -> dict[str, str]:
    path = resolve_db_path(db_path)
    if not table_names:
        return {}

    placeholders = ",".join("?" for _ in table_names)
    query = (
        "SELECT name, sql FROM sqlite_master "
        f"WHERE type = 'table' AND name IN ({placeholders}) ORDER BY name"
    )
    with sqlite3.connect(path) as conn:
        rows = conn.execute(query, tuple(table_names)).fetchall()
    return {str(name): str(sql or "") for name, sql in rows}


def ensure_safe_query(query: str) -> str:
    normalized = query.strip().rstrip(";")
    if not normalized:
        raise ValueError("SQL query must not be empty")

    upper_query = normalized.upper()
    if not upper_query.startswith(READ_ONLY_PREFIXES):
        raise ValueError("Only read-only SELECT queries are allowed")
    if any(token in upper_query for token in FORBIDDEN_TOKENS):
        raise ValueError("Only read-only SELECT queries are allowed")
    return normalized


def run_query(db_path: str | Path, query: str, max_rows: int = 20) -> list[dict[str, Any]]:
    safe_query = ensure_safe_query(query)
    path = resolve_db_path(db_path)

    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(safe_query)
        rows = cursor.fetchmany(max(max_rows, 1))

    return [dict(row) for row in rows]
