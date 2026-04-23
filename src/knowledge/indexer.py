from qdrant_client import models

from src.chunker import chunk_document
from src.knowledge.schemas import DocumentChunk, ParsedDocument
from src.knowledge.store import QdrantStore
from src.models.embeddings import embed_texts


class QdrantIndexer:
    def __init__(self, store: QdrantStore | None = None) -> None:
        self.store = store or QdrantStore()
        self.store.ensure_collection()

    def index_document(
        self,
        document: ParsedDocument,
        embedding_model: str | None = None,
    ) -> list[DocumentChunk]:
        chunks = chunk_document(document)
        self.index_chunks(chunks, embedding_model=embedding_model)
        return chunks

    def index_chunks(
        self,
        chunks: list[DocumentChunk],
        embedding_model: str | None = None,
    ) -> None:
        vectors = embed_texts([chunk.text for chunk in chunks], model=embedding_model)
        self.upsert_chunks(chunks, vectors)

    def upsert_chunks(
        self,
        chunks: list[DocumentChunk],
        vectors: list[list[float]],
    ) -> None:
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors must have the same length")

        points = [
            models.PointStruct(
                id=chunk.id,
                vector=vector,
                payload={
                    "doc_id": chunk.doc_id,
                    "source": chunk.source,
                    "index": chunk.index,
                    "text": chunk.text,
                    "markdown": chunk.markdown,
                    "headers": chunk.headers,
                    "metadata": chunk.metadata,
                },
            )
            for chunk, vector in zip(chunks, vectors)
        ]

        if not points:
            return

        self.store.client.upsert(
            collection_name=self.store.collection_name,
            points=points,
        )
