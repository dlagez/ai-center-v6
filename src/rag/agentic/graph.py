from langgraph.graph import END, START, StateGraph

from src.rag.agentic.nodes import (
    answer_directly,
    generate_answer,
    grade_documents,
    retrieve_documents,
    rewrite_question,
    route_question,
)
from src.rag.agentic.schemas import AgenticRagState


def _route_from_question(state: AgenticRagState) -> str:
    return "retrieve_documents" if state.get("route") == "retrieve" else "answer_directly"


def _route_after_grading(state: AgenticRagState) -> str:
    return "rewrite_question" if state.get("rewrite_needed") else "generate_answer"


def build_agentic_rag_graph():
    builder = StateGraph(AgenticRagState)
    builder.add_node("route_question", route_question)
    builder.add_node("retrieve_documents", retrieve_documents)
    builder.add_node("grade_documents", grade_documents)
    builder.add_node("rewrite_question", rewrite_question)
    builder.add_node("generate_answer", generate_answer)
    builder.add_node("answer_directly", answer_directly)

    builder.add_edge(START, "route_question")
    builder.add_conditional_edges(
        "route_question",
        _route_from_question,
        {
            "retrieve_documents": "retrieve_documents",
            "answer_directly": "answer_directly",
        },
    )
    builder.add_edge("retrieve_documents", "grade_documents")
    builder.add_conditional_edges(
        "grade_documents",
        _route_after_grading,
        {
            "rewrite_question": "rewrite_question",
            "generate_answer": "generate_answer",
        },
    )
    builder.add_edge("rewrite_question", "retrieve_documents")
    builder.add_edge("generate_answer", END)
    builder.add_edge("answer_directly", END)
    return builder.compile()


graph = build_agentic_rag_graph()
