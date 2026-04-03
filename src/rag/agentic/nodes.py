import json

from src.knowledge.retriever import QdrantRetriever
from src.knowledge.schemas import SearchResult
from src.models.llm import chat_completion
from src.observability import observe
from src.rag.agentic.prompts import ANSWER_PROMPT, GRADE_PROMPT, REWRITE_PROMPT, ROUTER_PROMPT
from src.rag.agentic.schemas import AgenticRagState

MAX_RETRIEVAL_ATTEMPTS = 2


def _parse_json_object(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise


def _format_docs(docs: list[SearchResult]) -> str:
    sections: list[str] = []
    for index, doc in enumerate(docs, start=1):
        headers = " > ".join(doc.headers)
        title = f"[Chunk {index}] source={doc.source}"
        if headers:
            title += f" headers={headers}"
        sections.append(f"{title}\n{doc.text}")
    return "\n\n".join(sections)


def route_question(state: AgenticRagState) -> AgenticRagState:
    question = state["question"]
    with observe(
        name="agentic.route_question",
        as_type="chain",
        input={"question": question},
    ) as observation:
        response = chat_completion(
            temperature=0,
            max_tokens=100,
            messages=[
                {"role": "system", "content": ROUTER_PROMPT},
                {"role": "user", "content": question},
            ],
        )
        payload = _parse_json_object(response)
        route = payload.get("route", "retrieve")
        if route not in {"retrieve", "answer"}:
            route = "retrieve"
        result = {"route": route, "retrieval_query": question}
        if observation is not None:
            observation.update(output=result)
        return result


def retrieve_documents(
    state: AgenticRagState,
    retriever: QdrantRetriever | None = None,
) -> AgenticRagState:
    active_retriever = retriever or QdrantRetriever()
    query = state.get("rewritten_question") or state.get("retrieval_query") or state["question"]
    limit = state.get("limit", 5)
    with observe(
        name="agentic.retrieve_documents",
        as_type="retriever",
        input={"query": query, "limit": limit},
    ) as observation:
        docs = active_retriever.search_text(query, limit=limit)
        attempts = state.get("retrieval_attempts", 0) + 1
        result = {
            "retrieved_docs": docs,
            "retrieval_query": query,
            "retrieval_attempts": attempts,
            "sources": docs,
        }
        if observation is not None:
            observation.update(output={"result_count": len(docs), "attempts": attempts})
        return result


def grade_documents(state: AgenticRagState) -> AgenticRagState:
    docs = state.get("retrieved_docs", [])
    with observe(
        name="agentic.grade_documents",
        as_type="evaluator",
        input={
            "question": state["question"],
            "retrieval_attempts": state.get("retrieval_attempts", 0),
            "document_count": len(docs),
        },
    ) as observation:
        if not docs:
            result = {"rewrite_needed": True}
            if observation is not None:
                observation.update(output=result)
            return result

        response = chat_completion(
            temperature=0,
            max_tokens=100,
            messages=[
                {"role": "system", "content": GRADE_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Question: {state['question']}\n\n"
                        f"Retrieved context:\n{_format_docs(docs)}"
                    ),
                },
            ],
        )
        payload = _parse_json_object(response)
        relevant = bool(payload.get("relevant", False))
        rewrite_needed = not relevant and state.get("retrieval_attempts", 0) < MAX_RETRIEVAL_ATTEMPTS
        result = {"rewrite_needed": rewrite_needed}
        if observation is not None:
            observation.update(output={"relevant": relevant, **result})
        return result


def rewrite_question(state: AgenticRagState) -> AgenticRagState:
    with observe(
        name="agentic.rewrite_question",
        as_type="chain",
        input={"question": state["question"]},
    ) as observation:
        rewritten = chat_completion(
            temperature=0,
            max_tokens=120,
            messages=[
                {"role": "system", "content": REWRITE_PROMPT},
                {"role": "user", "content": state["question"]},
            ],
        ).strip()
        result = {"rewritten_question": rewritten, "retrieval_query": rewritten}
        if observation is not None:
            observation.update(output=result)
        return result


def answer_directly(state: AgenticRagState) -> AgenticRagState:
    with observe(
        name="agentic.answer_directly",
        as_type="chain",
        input={"question": state["question"]},
    ) as observation:
        answer = chat_completion(
            temperature=0,
            max_tokens=500,
            messages=[
                {"role": "system", "content": "You are a concise enterprise assistant."},
                {"role": "user", "content": state["question"]},
            ],
        )
        result = {"answer": answer, "sources": []}
        if observation is not None:
            observation.update(output={"answer_length": len(answer)})
        return result


def generate_answer(state: AgenticRagState) -> AgenticRagState:
    docs = state.get("retrieved_docs", [])
    context = _format_docs(docs)
    with observe(
        name="agentic.generate_answer",
        as_type="chain",
        input={
            "question": state["question"],
            "retrieval_query": state.get("retrieval_query"),
            "document_count": len(docs),
        },
    ) as observation:
        answer = chat_completion(
            temperature=0,
            max_tokens=1200,
            messages=[
                {"role": "system", "content": ANSWER_PROMPT},
                {
                    "role": "user",
                    "content": f"Question: {state['question']}\n\nRetrieved context:\n{context}",
                },
            ],
        )
        result = {"answer": answer, "sources": docs}
        if observation is not None:
            observation.update(output={"answer_length": len(answer), "source_count": len(docs)})
        return result
