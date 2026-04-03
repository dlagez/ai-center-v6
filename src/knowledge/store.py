from qdrant_client import QdrantClient, models

from src.config.settings import settings


class QdrantStore:
    def __init__(self) -> None:
        self.client = QdrantClient(path=settings.qdrant_path)
        self.collection_name = settings.qdrant_collection

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> "QdrantStore":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def ensure_collection(self) -> None:
        collections = self.client.get_collections().collections
        exists = any(collection.name == self.collection_name for collection in collections)

        if not exists:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=settings.embedding_dimension,
                    distance=models.Distance.COSINE,
                ),
            )
