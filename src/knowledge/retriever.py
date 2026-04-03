from src.knowledge.schemas import SearchResult
from src.knowledge.store import QdrantStore


class QdrantRetriever:
    def __init__(self, store: QdrantStore | None = None) -> None:
        self.store = store or QdrantStore()
        self.store.ensure_collection()

    def search(self, query_vector: list[float], limit: int = 5) -> list[SearchResult]:
        results = self.store.client.query_points(
            collection_name=self.store.collection_name,
            query=query_vector,
            limit=limit,
        ).points

        return [
            SearchResult(
                source=str(point.payload.get("source", "")),
                index=int(point.payload.get("index", 0)),
                text=str(point.payload.get("text", "")),
                score=float(point.score),
            )
            for point in results
        ]
