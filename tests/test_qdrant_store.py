from src.config.settings import settings
from src.knowledge.store import QdrantStore


def test_qdrant_store_ensure_collection(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "qdrant_path", str(tmp_path / "qdrant"))
    monkeypatch.setattr(settings, "qdrant_collection", "test_collection")

    with QdrantStore() as store:
        store.ensure_collection()

        collections = store.client.get_collections().collections
        assert any(collection.name == store.collection_name for collection in collections)
