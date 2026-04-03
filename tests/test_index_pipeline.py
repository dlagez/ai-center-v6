from src.config.settings import settings
from src.knowledge.indexer import QdrantIndexer
from src.knowledge.retriever import QdrantRetriever
from src.knowledge.schemas import ParsedDocument
from src.knowledge.store import QdrantStore


def test_index_and_retrieve_roundtrip(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "qdrant_path", str(tmp_path / "qdrant"))
    monkeypatch.setattr(settings, "qdrant_collection", "pipeline_collection")
    monkeypatch.setattr(settings, "embedding_dimension", 3)

    def fake_embed_texts(texts, model=None, **kwargs):
        vectors = []
        for text in texts:
            lowered = text.lower()
            if "alpha" in lowered:
                vectors.append([1.0, 0.0, 0.0])
            elif "beta" in lowered:
                vectors.append([0.0, 1.0, 0.0])
            else:
                vectors.append([0.0, 0.0, 1.0])
        return vectors

    monkeypatch.setattr("src.knowledge.indexer.embed_texts", fake_embed_texts)
    monkeypatch.setattr("src.knowledge.retriever.embed_query", lambda *args, **kwargs: [1.0, 0.0, 0.0])

    document = ParsedDocument(
        doc_id="doc-alpha",
        source="alpha.md",
        markdown="# Alpha\n\nAlpha section.\n\n## Beta\n\nBeta section.",
        text="Alpha section. Beta section.",
    )

    with QdrantStore() as store:
        indexer = QdrantIndexer(store=store)
        retriever = QdrantRetriever(store=store)

        chunks = indexer.index_document(document)
        results = retriever.search_text("alpha", limit=1)

    assert len(chunks) >= 1
    assert results[0].source == "alpha.md"
    assert "Alpha" in results[0].text
