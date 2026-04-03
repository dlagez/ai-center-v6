import json

from src.knowledge.retriever import QdrantRetriever
from src.knowledge.schemas import SearchResult
from src.models.llm import chat_completion
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
    return {"route": route, "retrieval_query": question}


def retrieve_documents(
    state: AgenticRagState,
    retriever: QdrantRetriever | None = None,
) -> AgenticRagState:
    active_retriever = retriever or QdrantRetriever()
    query = state.get("rewritten_question") or state.get("retrieval_query") or state["question"]
    limit = state.get("limit", 5)
    docs = active_retriever.search_text(query, limit=limit)
    attempts = state.get("retrieval_attempts", 0) + 1
    return {
        "retrieved_docs": docs,
        "retrieval_query": query,
        "retrieval_attempts": attempts,
        "sources": docs,
    }


def grade_documents(state: AgenticRagState) -> AgenticRagState:
    docs = state.get("retrieved_docs", [])
    if not docs:
        return {"rewrite_needed": True}

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
    return {"rewrite_needed": rewrite_needed}


def rewrite_question(state: AgenticRagState) -> AgenticRagState:
    rewritten = chat_completion(
        temperature=0,
        max_tokens=120,
        messages=[
            {"role": "system", "content": REWRITE_PROMPT},
            {"role": "user", "content": state["question"]},
        ],
    ).strip()
    return {"rewritten_question": rewritten, "retrieval_query": rewritten}


def answer_directly(state: AgenticRagState) -> AgenticRagState:
    answer = chat_completion(
        temperature=0,
        max_tokens=500,
        messages=[
            {"role": "system", "content": "You are a concise enterprise assistant."},
            {"role": "user", "content": state["question"]},
        ],
    )
    return {"answer": answer, "sources": []}


def generate_answer(state: AgenticRagState) -> AgenticRagState:
    docs = state.get("retrieved_docs", [])
    context = _format_docs(docs)
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
    return {"answer": answer, "sources": docs}
