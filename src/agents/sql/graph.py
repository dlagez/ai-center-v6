from langgraph.graph import END, START, StateGraph

from src.agents.sql.nodes import (
    check_query,
    generate_answer,
    generate_query,
    list_database_tables,
    load_selected_schema,
    run_sql_query,
    select_relevant_tables,
)
from src.agents.sql.schemas import SqlAgentState


def _route_after_generate(state: SqlAgentState) -> str:
    return "generate_answer" if not state.get("sql_query") else "check_query"


def _route_after_run(state: SqlAgentState) -> str:
    has_error = bool(state.get("query_error"))
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 2)
    if has_error and retry_count < max_retries:
        return "generate_query"
    return "generate_answer"


def build_sql_agent_graph():
    builder = StateGraph(SqlAgentState)
    builder.add_node("list_database_tables", list_database_tables)
    builder.add_node("select_relevant_tables", select_relevant_tables)
    builder.add_node("load_selected_schema", load_selected_schema)
    builder.add_node("generate_query", generate_query)
    builder.add_node("check_query", check_query)
    builder.add_node("run_sql_query", run_sql_query)
    builder.add_node("generate_answer", generate_answer)

    builder.add_edge(START, "list_database_tables")
    builder.add_edge("list_database_tables", "select_relevant_tables")
    builder.add_edge("select_relevant_tables", "load_selected_schema")
    builder.add_edge("load_selected_schema", "generate_query")
    builder.add_conditional_edges(
        "generate_query",
        _route_after_generate,
        {
            "check_query": "check_query",
            "generate_answer": "generate_answer",
        },
    )
    builder.add_edge("check_query", "run_sql_query")
    builder.add_conditional_edges(
        "run_sql_query",
        _route_after_run,
        {
            "generate_query": "generate_query",
            "generate_answer": "generate_answer",
        },
    )
    builder.add_edge("generate_answer", END)
    return builder.compile()


graph = build_sql_agent_graph()
