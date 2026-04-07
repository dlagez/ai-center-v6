import sqlite3
from pathlib import Path
from typing import Any

import pymysql

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


def resolve_mysql_config(mysql_config: dict[str, Any] | None) -> dict[str, Any]:
    config = dict(mysql_config or {})
    required_keys = ("host", "port", "user", "password", "database")
    missing = [key for key in required_keys if not config.get(key)]
    if missing:
        raise ValueError(f"Missing MySQL connection settings: {', '.join(missing)}")
    return config


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


def list_tables_mysql(mysql_config: dict[str, Any]) -> list[str]:
    config = resolve_mysql_config(mysql_config)
    connection = pymysql.connect(
        host=config["host"],
        port=int(config["port"]),
        user=config["user"],
        password=config["password"],
        database=config["database"],
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute("SHOW TABLES")
            rows = cursor.fetchall()
    finally:
        connection.close()

    table_names: list[str] = []
    for row in rows:
        table_names.extend(str(value) for value in row.values())
    return table_names


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


def get_schema_mysql(mysql_config: dict[str, Any], table_names: list[str]) -> dict[str, str]:
    config = resolve_mysql_config(mysql_config)
    if not table_names:
        return {}

    schema: dict[str, str] = {}
    connection = pymysql.connect(
        host=config["host"],
        port=int(config["port"]),
        user=config["user"],
        password=config["password"],
        database=config["database"],
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )
    try:
        with connection.cursor() as cursor:
            for table_name in table_names:
                cursor.execute(f"SHOW CREATE TABLE `{table_name}`")
                row = cursor.fetchone() or {}
                create_sql = row.get("Create Table") or row.get("Create View") or ""
                schema[table_name] = str(create_sql)
    finally:
        connection.close()
    return schema


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


def run_query_mysql(
    mysql_config: dict[str, Any],
    query: str,
    max_rows: int = 20,
) -> list[dict[str, Any]]:
    safe_query = ensure_safe_query(query)
    config = resolve_mysql_config(mysql_config)
    limited_query = safe_query
    if " LIMIT " not in safe_query.upper():
        limited_query = f"{safe_query} LIMIT {max(max_rows, 1)}"

    connection = pymysql.connect(
        host=config["host"],
        port=int(config["port"]),
        user=config["user"],
        password=config["password"],
        database=config["database"],
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute(limited_query)
            rows = cursor.fetchall()
    finally:
        connection.close()

    return [dict(row) for row in rows]
