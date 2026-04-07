import sqlite3
from pathlib import Path

from src.agents.sql.db import ensure_db_file
from src.agents.sql.graph import build_sql_agent_graph
from src.agents.sql.service import SqlAgentService


def _create_demo_db(db_path: Path) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE sales (
                id INTEGER PRIMARY KEY,
                region TEXT NOT NULL,
                amount INTEGER NOT NULL
            )
            """
        )
        conn.executemany(
            "INSERT INTO sales(region, amount) VALUES(?, ?)",
            [
                ("East", 120),
                ("West", 90),
                ("East", 80),
            ],
        )
        conn.commit()


def test_sql_agent_service_answers_question(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "demo.db"
    _create_demo_db(db_path)

    def fake_chat_completion(messages, **kwargs):
        system_prompt = messages[0]["content"]
        if "Select the tables" in system_prompt:
            return '{"tables": ["sales"]}'
        if "Write exactly one read-only SQLite query" in system_prompt:
            return "SELECT region, SUM(amount) AS total_amount FROM sales GROUP BY region ORDER BY total_amount DESC"
        if "reviewing a sqlite query" in system_prompt.lower():
            return "SELECT region, SUM(amount) AS total_amount FROM sales GROUP BY region ORDER BY total_amount DESC"
        if "concise data analyst" in system_prompt:
            return "East has the highest total amount with 200."
        raise AssertionError(f"Unexpected prompt: {system_prompt}")

    monkeypatch.setattr("src.agents.sql.nodes.chat_completion", fake_chat_completion)

    service = SqlAgentService(graph=build_sql_agent_graph())
    result = service.answer("Which region has the highest sales?", db_path=db_path, max_rows=10)

    assert result.sql_query.startswith("SELECT region")
    assert result.rows[0]["region"] == "East"
    assert result.answer == "East has the highest total amount with 200."
    assert result.error is None


def test_sql_agent_service_rejects_missing_db_path(monkeypatch) -> None:
    monkeypatch.setattr("src.agents.sql.service.settings.sql_agent_default_db_path", None)
    service = SqlAgentService(graph=build_sql_agent_graph())

    try:
        service.answer("Which region has the highest sales?")
    except ValueError as exc:
        assert str(exc) == "Database path must be provided"
    else:
        raise AssertionError("Expected ValueError")


def test_sql_agent_service_creates_missing_db_file(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "new" / "empty.db"

    def fake_chat_completion(messages, **kwargs):
        system_prompt = messages[0]["content"]
        if "concise data analyst" in system_prompt:
            return "The database file was created, but it has no tables yet."
        raise AssertionError(f"Unexpected prompt: {system_prompt}")

    monkeypatch.setattr("src.agents.sql.nodes.chat_completion", fake_chat_completion)

    service = SqlAgentService(graph=build_sql_agent_graph())
    result = service.answer("Which region has the highest sales?", db_path=db_path, max_rows=10)

    assert db_path.exists()
    assert result.rows == []
    assert result.sql_query == ""
    assert result.error == "The database has no tables yet. Create tables and load data first."
    assert result.answer == "The database file was created, but it has no tables yet."


def test_ensure_db_file_creates_parent_directories(tmp_path: Path) -> None:
    db_path = tmp_path / "nested" / "demo.db"
    created = ensure_db_file(db_path)

    assert created == db_path
    assert db_path.exists()
    assert db_path.is_file()
