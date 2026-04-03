from fastapi.testclient import TestClient

from src.api.app import app
from src.knowledge.schemas import SearchResult, SearchSummary

client = TestClient(app)


def test_search_endpoint_returns_results(monkeypatch) -> None:
    class _FakeService:
        def search(self, query, limit=5):
            assert query == "什么是RAG"
            assert limit == 3
            return SearchSummary(
                query=query,
                limit=limit,
                collection="ai-center",
                results=[
                    SearchResult(
                        id="1",
                        doc_id="doc-1",
                        source="demo.pdf",
                        index=0,
                        text="RAG 是检索增强生成。",
                        score=0.95,
                        headers=["RAG"],
                    )
                ],
            )

    monkeypatch.setattr("src.api.routes.KnowledgeSearchService", lambda: _FakeService())

    response = client.post(
        "/knowledge/search",
        json={"query": "什么是RAG", "limit": 3},
    )

    assert response.status_code == 200
    assert response.json()["collection"] == "ai-center"
    assert response.json()["results"][0]["source"] == "demo.pdf"


def test_search_endpoint_maps_validation_errors(monkeypatch) -> None:
    class _FakeService:
        def search(self, query, limit=5):
            raise ValueError("Query must not be empty")

    monkeypatch.setattr("src.api.routes.KnowledgeSearchService", lambda: _FakeService())

    response = client.post("/knowledge/search", json={"query": "x", "limit": 5})

    assert response.status_code == 400
    assert response.json()["detail"] == "Query must not be empty"
