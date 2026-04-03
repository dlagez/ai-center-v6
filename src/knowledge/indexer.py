from qdrant_client import models

from src.knowledge.schemas import DocumentChunk
from src.knowledge.store import QdrantStore


class QdrantIndexer:
    def __init__(self, store: QdrantStore | None = None) -> None:
        self.store = store or QdrantStore()
        self.store.ensure_collection()

    def upsert_chunks(
        self,
        chunks: list[DocumentChunk],
        vectors: list[list[float]],
    ) -> None:
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors must have the same length")

        points = [
            models.PointStruct(
                id=index,
                vector=vector,
                payload={
                    "source": chunk.source,
                    "index": chunk.index,
                    "text": chunk.text,
                },
            )
            for index, (chunk, vector) in enumerate(zip(chunks, vectors))
        ]

        if not points:
            return

        self.store.client.upsert(
            collection_name=self.store.collection_name,
            points=points,
        )
