from src.knowledge.retriever import QdrantRetriever
from src.observability import current_trace_info, observe
from src.rag.schemas import SearchSummary


class KnowledgeSearchService:
    def __init__(self, retriever: QdrantRetriever | None = None) -> None:
        self.retriever = retriever or QdrantRetriever()

    def search(self, query: str, limit: int = 5) -> SearchSummary:
        query_text = query.strip()
        if not query_text:
            raise ValueError("Query must not be empty")
        if limit <= 0:
            raise ValueError("Limit must be greater than 0")

        with observe(
            name="knowledge.search",
            as_type="retriever",
            input={"query": query_text, "limit": limit},
            metadata={"collection": self.retriever.store.collection_name},
        ) as observation:
            results = self.retriever.search_text(query_text, limit=limit)
            trace_id, trace_url = current_trace_info()
            summary = SearchSummary(
                query=query_text,
                limit=limit,
                collection=self.retriever.store.collection_name,
                results=results,
                trace_id=trace_id,
                trace_url=trace_url,
            )
            if observation is not None:
                observation.update(output={"result_count": len(results)})
            return summary
