from src.knowledge.store import QdrantStore


def test_qdrant_store_ensure_collection() -> None:
    with QdrantStore() as store:
        store.ensure_collection()

        collections = store.client.get_collections().collections
        assert any(collection.name == store.collection_name for collection in collections)
