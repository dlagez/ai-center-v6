from fastapi.testclient import TestClient

from src.api.app import app
from src.knowledge.schemas import SearchResult
from src.rag.agentic.schemas import AgenticRagOutput

client = TestClient(app)


def test_agentic_rag_endpoint_returns_answer(monkeypatch) -> None:
    class _FakeService:
        def answer(self, question, limit=5):
            assert question == "What is the basic idea?"
            assert limit == 3
            return AgenticRagOutput(
                question=question,
                answer="The basic idea is to validate retrieval first.",
                retrieval_attempts=2,
                retrieval_query="rewritten basic idea query",
                sources=[
                    SearchResult(
                        id="1",
                        doc_id="doc-1",
                        source="demo.md",
                        index=0,
                        text="The core idea is to build an offline evaluation set first.",
                        score=0.95,
                        headers=["Core idea"],
                    )
                ],
            )

    monkeypatch.setattr("src.api.routes.AgenticRagService", lambda: _FakeService())

    response = client.post(
        "/rag/agentic-answer",
        json={"question": "What is the basic idea?", "limit": 3},
    )

    assert response.status_code == 200
    assert response.json()["retrieval_attempts"] == 2
    assert response.json()["sources"][0]["source"] == "demo.md"


def test_agentic_rag_endpoint_maps_validation_errors(monkeypatch) -> None:
    class _FakeService:
        def answer(self, question, limit=5):
            raise ValueError("Question must not be empty")

    monkeypatch.setattr("src.api.routes.AgenticRagService", lambda: _FakeService())

    response = client.post("/rag/agentic-answer", json={"question": "x", "limit": 5})

    assert response.status_code == 400
    assert response.json()["detail"] == "Question must not be empty"
