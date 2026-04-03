from src.knowledge.schemas import SearchResult
from src.rag.agentic import nodes
from src.rag.agentic.graph import build_agentic_rag_graph


class _FakeRetriever:
    def search_text(self, query, limit=5):
        if "rewritten" in query:
            return [
                SearchResult(
                    id="1",
                    doc_id="doc-1",
                    source="demo.md",
                    index=0,
                    text="The core idea is to build an offline evaluation set first.",
                    score=0.95,
                    headers=["Core idea"],
                )
            ]
        return []


def test_agentic_rag_graph_rewrites_then_answers(monkeypatch) -> None:
    responses = iter(
        [
            '{"route":"retrieve"}',
            '{"relevant": false}',
            "rewritten query about the basic idea",
            '{"relevant": true}',
            "The basic idea is to validate retrieval first.\n\nSources:\n- demo.md",
        ]
    )

    monkeypatch.setattr(nodes, "chat_completion", lambda *args, **kwargs: next(responses))
    monkeypatch.setattr(nodes, "QdrantRetriever", lambda: _FakeRetriever())

    graph = build_agentic_rag_graph()
    result = graph.invoke({"question": "What is the basic idea?", "limit": 3})

    assert result["retrieval_attempts"] >= 2
    assert result["retrieval_query"] == "rewritten query about the basic idea"
    assert "validate retrieval first" in result["answer"]
    assert result["sources"][0].source == "demo.md"


def test_agentic_rag_graph_can_answer_directly(monkeypatch) -> None:
    responses = iter(
        [
            '{"route":"answer"}',
            "Hello there.",
        ]
    )

    monkeypatch.setattr(nodes, "chat_completion", lambda *args, **kwargs: next(responses))

    graph = build_agentic_rag_graph()
    result = graph.invoke({"question": "Hi", "limit": 3})

    assert result["answer"] == "Hello there."
    assert result["sources"] == []
