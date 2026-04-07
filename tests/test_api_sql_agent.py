from fastapi.testclient import TestClient

from src.agents.sql.schemas import SqlAgentOutput
from src.api.app import app

client = TestClient(app)


def test_sql_agent_endpoint_returns_answer(monkeypatch) -> None:
    class _FakeService:
        def answer(self, question, db_path=None, max_rows=20):
            assert question == "Which region has the highest sales?"
            assert db_path == "demo.db"
            assert max_rows == 10
            return SqlAgentOutput(
                question=question,
                db_path=db_path,
                sql_query="SELECT region, SUM(amount) AS total_amount FROM sales GROUP BY region",
                rows=[{"region": "East", "total_amount": 200}],
                answer="East has the highest total amount with 200.",
                error=None,
            )

    monkeypatch.setattr("src.api.routes.SqlAgentService", lambda: _FakeService())

    response = client.post(
        "/agents/sql",
        json={
            "question": "Which region has the highest sales?",
            "db_path": "demo.db",
            "max_rows": 10,
        },
    )

    assert response.status_code == 200
    assert response.json()["rows"][0]["region"] == "East"


def test_sql_agent_endpoint_maps_validation_errors(monkeypatch) -> None:
    class _FakeService:
        def answer(self, question, db_path=None, max_rows=20):
            raise ValueError("Database path must be provided")

    monkeypatch.setattr("src.api.routes.SqlAgentService", lambda: _FakeService())

    response = client.post(
        "/agents/sql",
        json={"question": "Which region has the highest sales?", "max_rows": 10},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Database path must be provided"
