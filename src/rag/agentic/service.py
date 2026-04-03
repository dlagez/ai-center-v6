from src.rag.agentic.graph import build_agentic_rag_graph
from src.rag.agentic.schemas import AgenticRagInput, AgenticRagOutput
from src.observability import current_trace_info, observe


class AgenticRagService:
    def __init__(self, graph=None) -> None:
        self.graph = graph or build_agentic_rag_graph()

    def answer(self, question: str, limit: int = 5) -> AgenticRagOutput:
        question_text = question.strip()
        if not question_text:
            raise ValueError("Question must not be empty")
        if limit <= 0:
            raise ValueError("Limit must be greater than 0")

        with observe(
            name="rag.agentic_answer",
            as_type="agent",
            input={"question": question_text, "limit": limit},
        ) as observation:
            result = self.graph.invoke({"question": question_text, "limit": limit})
            trace_id, trace_url = current_trace_info()
            output = AgenticRagOutput(
                question=question_text,
                answer=result.get("answer", ""),
                retrieval_attempts=result.get("retrieval_attempts", 0),
                retrieval_query=result.get("retrieval_query", question_text),
                sources=result.get("sources", []),
                trace_id=trace_id,
                trace_url=trace_url,
            )
            if observation is not None:
                observation.update(
                    output={
                        "retrieval_attempts": output.retrieval_attempts,
                        "source_count": len(output.sources),
                    }
                )
            return output
