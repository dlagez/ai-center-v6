from src.knowledge.schemas import SearchResult
from src.knowledge.store import QdrantStore
from src.models.embeddings import embed_query


class QdrantRetriever:
    def __init__(self, store: QdrantStore | None = None) -> None:
        self.store = store or QdrantStore()
        self.store.ensure_collection()

    def search_text(
        self,
        query_text: str,
        limit: int = 5,
        embedding_model: str | None = None,
    ) -> list[SearchResult]:
        query_vector = embed_query(query_text, model=embedding_model)
        return self.search(query_vector, limit=limit)

    def search(self, query_vector: list[float], limit: int = 5) -> list[SearchResult]:
        results = self.store.client.query_points(
            collection_name=self.store.collection_name,
            query=query_vector,
            limit=limit,
        ).points

        return [
            SearchResult(
                id=str(point.id),
                doc_id=str(point.payload.get("doc_id", "")),
                source=str(point.payload.get("source", "")),
                index=int(point.payload.get("index", 0)),
                text=str(point.payload.get("text", "")),
                score=float(point.score),
                headers=list(point.payload.get("headers", [])),
                metadata=dict(point.payload.get("metadata", {})),
            )
            for point in results
        ]
