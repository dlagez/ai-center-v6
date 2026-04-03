from src.knowledge.schemas import SearchResult
from src.rag.service import KnowledgeSearchService


def test_search_service_returns_summary() -> None:
    class _FakeRetriever:
        def __init__(self) -> None:
            self.store = type("Store", (), {"collection_name": "ai-center"})()

        def search_text(self, query_text: str, limit: int = 5):
            assert query_text == "hello"
            assert limit == 2
            return [
                SearchResult(
                    id="1",
                    doc_id="doc-1",
                    source="a.md",
                    index=0,
                    text="hello world",
                    score=0.9,
                    headers=["H1"],
                )
            ]

    summary = KnowledgeSearchService(retriever=_FakeRetriever()).search("hello", limit=2)

    assert summary.collection == "ai-center"
    assert len(summary.results) == 1
    assert summary.results[0].text == "hello world"


def test_search_service_rejects_empty_query() -> None:
    class _FakeRetriever:
        def __init__(self) -> None:
            self.store = type("Store", (), {"collection_name": "ai-center"})()

        def search_text(self, query_text: str, limit: int = 5):
            return []

    service = KnowledgeSearchService(retriever=_FakeRetriever())

    try:
        service.search("   ")
    except ValueError as exc:
        assert str(exc) == "Query must not be empty"
    else:
        raise AssertionError("Expected ValueError")
