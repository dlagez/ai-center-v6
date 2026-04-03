from src.rag.agentic.graph import build_agentic_rag_graph
from src.rag.agentic.schemas import AgenticRagInput, AgenticRagOutput


class AgenticRagService:
    def __init__(self, graph=None) -> None:
        self.graph = graph or build_agentic_rag_graph()

    def answer(self, question: str, limit: int = 5) -> AgenticRagOutput:
        question_text = question.strip()
        if not question_text:
            raise ValueError("Question must not be empty")
        if limit <= 0:
            raise ValueError("Limit must be greater than 0")

        result = self.graph.invoke({"question": question_text, "limit": limit})
        return AgenticRagOutput(
            question=question_text,
            answer=result.get("answer", ""),
            retrieval_attempts=result.get("retrieval_attempts", 0),
            retrieval_query=result.get("retrieval_query", question_text),
            sources=result.get("sources", []),
        )
