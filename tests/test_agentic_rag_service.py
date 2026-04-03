from src.knowledge.schemas import SearchResult
from src.rag.agentic.service import AgenticRagService


class _FakeGraph:
    def invoke(self, state):
        assert state["question"] == "What is the approach?"
        assert state["limit"] == 3
        return {
            "answer": "The approach is to retrieve, grade, rewrite, and answer.",
            "retrieval_attempts": 2,
            "retrieval_query": "rewritten approach query",
            "sources": [
                SearchResult(
                    id="1",
                    doc_id="doc-1",
                    source="demo.md",
                    index=0,
                    text="Agentic RAG loops through retrieval and grading.",
                    score=0.9,
                    headers=["Overview"],
                )
            ],
        }


def test_agentic_rag_service_returns_output() -> None:
    service = AgenticRagService(graph=_FakeGraph())
    output = service.answer("What is the approach?", limit=3)

    assert output.retrieval_attempts == 2
    assert output.retrieval_query == "rewritten approach query"
    assert output.sources[0].source == "demo.md"


def test_agentic_rag_service_rejects_empty_question() -> None:
    service = AgenticRagService(graph=_FakeGraph())

    try:
        service.answer("   ")
    except ValueError as exc:
        assert str(exc) == "Question must not be empty"
    else:
        raise AssertionError("Expected ValueError")
