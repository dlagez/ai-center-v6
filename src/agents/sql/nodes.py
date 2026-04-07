import json
from typing import Any

from src.agents.sql.db import (
    get_schema,
    get_schema_mysql,
    list_tables,
    list_tables_mysql,
    run_query,
    run_query_mysql,
)
from src.agents.sql.prompts import (
    ANSWER_PROMPT,
    QUERY_CHECK_PROMPT,
    QUERY_GENERATION_PROMPT,
    TABLE_SELECTION_PROMPT,
)
from src.agents.sql.schemas import SqlAgentState
from src.models.llm import chat_completion
from src.observability import observe


def _parse_json_object(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise


def _strip_code_fence(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        parts = cleaned.split("```")
        if len(parts) >= 3:
            cleaned = parts[1]
            if "\n" in cleaned:
                cleaned = cleaned.split("\n", 1)[1]
    return cleaned.strip().rstrip(";")


def _format_schema(schema: dict[str, str]) -> str:
    return "\n\n".join(f"{name}:\n{ddl}" for name, ddl in schema.items())


def _dialect_label(state: SqlAgentState) -> str:
    return "MySQL" if state.get("dialect") == "mysql" else "SQLite"


def list_database_tables(state: SqlAgentState) -> SqlAgentState:
    db_path = state["db_path"]
    dialect = state.get("dialect", "sqlite")
    with observe(
        name="sql_agent.list_tables",
        as_type="tool",
        input={"db_path": db_path, "dialect": dialect},
    ) as observation:
        if dialect == "mysql":
            table_names = list_tables_mysql(state.get("mysql_config", {}))
        else:
            table_names = list_tables(db_path)
        result = {"table_names": table_names}
        if observation is not None:
            observation.update(output=result)
        return result


def select_relevant_tables(state: SqlAgentState) -> SqlAgentState:
    table_names = state.get("table_names", [])
    if not table_names:
        return {"selected_tables": []}

    with observe(
        name="sql_agent.select_tables",
        as_type="chain",
        input={"question": state["question"], "table_names": table_names},
    ) as observation:
        response = chat_completion(
            temperature=0,
            max_tokens=200,
            messages=[
                {"role": "system", "content": TABLE_SELECTION_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Dialect: {_dialect_label(state)}\n\n"
                        f"Question: {state['question']}\n\n"
                        f"Available tables: {', '.join(table_names)}"
                    ),
                },
            ],
        )
        payload = _parse_json_object(response)
        selected = [name for name in payload.get("tables", []) if name in table_names]
        if not selected:
            selected = table_names
        result = {"selected_tables": selected}
        if observation is not None:
            observation.update(output=result)
        return result


def load_selected_schema(state: SqlAgentState) -> SqlAgentState:
    selected_tables = state.get("selected_tables") or state.get("table_names", [])
    with observe(
        name="sql_agent.get_schema",
        as_type="tool",
        input={
            "db_path": state["db_path"],
            "dialect": state.get("dialect", "sqlite"),
            "selected_tables": selected_tables,
        },
    ) as observation:
        if state.get("dialect") == "mysql":
            schema = get_schema_mysql(state.get("mysql_config", {}), selected_tables)
        else:
            schema = get_schema(state["db_path"], selected_tables)
        schema_text = _format_schema(schema)
        result = {"schema": schema, "schema_text": schema_text}
        if observation is not None:
            observation.update(output={"table_count": len(schema)})
        return result


def generate_query(state: SqlAgentState) -> SqlAgentState:
    if not state.get("schema_text", "").strip():
        return {
            "sql_query": "",
            "query_error": "The database has no tables yet. Create tables and load data first.",
        }

    with observe(
        name="sql_agent.generate_query",
        as_type="chain",
        input={
            "question": state["question"],
            "schema_text": state.get("schema_text", ""),
            "query_error": state.get("query_error"),
        },
    ) as observation:
        messages = [
            {"role": "system", "content": QUERY_GENERATION_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Dialect: {_dialect_label(state)}\n\n"
                    f"Question: {state['question']}\n\n"
                    f"Schema:\n{state.get('schema_text', '')}"
                ),
            },
        ]
        if state.get("query_error"):
            messages.append(
                {
                    "role": "user",
                    "content": f"The previous query failed with this error: {state['query_error']}",
                }
            )
        sql_query = _strip_code_fence(
            chat_completion(
                temperature=0,
                max_tokens=400,
                messages=messages,
            )
        )
        result = {"sql_query": sql_query, "query_error": None}
        if observation is not None:
            observation.update(output=result)
        return result


def check_query(state: SqlAgentState) -> SqlAgentState:
    if not state.get("sql_query", "").strip():
        return {"sql_query": "", "query_error": state.get("query_error")}

    with observe(
        name="sql_agent.check_query",
        as_type="chain",
        input={
            "question": state["question"],
            "schema_text": state.get("schema_text", ""),
            "sql_query": state.get("sql_query", ""),
        },
    ) as observation:
        checked_query = _strip_code_fence(
            chat_completion(
                temperature=0,
                max_tokens=400,
                messages=[
                    {"role": "system", "content": QUERY_CHECK_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            f"Dialect: {_dialect_label(state)}\n\n"
                            f"Question: {state['question']}\n\n"
                            f"Schema:\n{state.get('schema_text', '')}\n\n"
                            f"Query:\n{state.get('sql_query', '')}"
                        ),
                    },
                ],
            )
        )
        result = {"sql_query": checked_query}
        if observation is not None:
            observation.update(output=result)
        return result


def run_sql_query(state: SqlAgentState) -> SqlAgentState:
    retry_count = state.get("retry_count", 0) + 1
    sql_query = state.get("sql_query", "")
    if not sql_query.strip():
        return {
            "query_result": [],
            "query_error": state.get("query_error") or "No SQL query generated",
            "retry_count": retry_count,
        }
    with observe(
        name="sql_agent.run_query",
        as_type="tool",
        input={
            "db_path": state["db_path"],
            "dialect": state.get("dialect", "sqlite"),
            "sql_query": sql_query,
            "max_rows": state.get("max_rows", 20),
            "retry_count": retry_count,
        },
    ) as observation:
        try:
            if state.get("dialect") == "mysql":
                rows = run_query_mysql(
                    state.get("mysql_config", {}),
                    sql_query,
                    max_rows=state.get("max_rows", 20),
                )
            else:
                rows = run_query(
                    state["db_path"],
                    sql_query,
                    max_rows=state.get("max_rows", 20),
                )
            result = {
                "query_result": rows,
                "query_error": None,
                "retry_count": retry_count,
            }
            if observation is not None:
                observation.update(output={"row_count": len(rows), "retry_count": retry_count})
            return result
        except Exception as exc:
            result = {
                "query_result": [],
                "query_error": str(exc),
                "retry_count": retry_count,
            }
            if observation is not None:
                observation.update(output=result, level="ERROR", status_message=str(exc))
            return result


def generate_answer(state: SqlAgentState) -> SqlAgentState:
    rows = state.get("query_result", [])
    with observe(
        name="sql_agent.generate_answer",
        as_type="chain",
        input={
            "question": state["question"],
            "sql_query": state.get("sql_query", ""),
            "rows": rows,
            "query_error": state.get("query_error"),
        },
    ) as observation:
        answer = chat_completion(
            temperature=0,
            max_tokens=500,
            messages=[
                {"role": "system", "content": ANSWER_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Dialect: {_dialect_label(state)}\n\n"
                        f"Question: {state['question']}\n\n"
                        f"SQL Query:\n{state.get('sql_query', '')}\n\n"
                        f"Query Error: {state.get('query_error')}\n\n"
                        f"Query Result:\n{json.dumps(rows, ensure_ascii=False, indent=2)}"
                    ),
                },
            ],
        )
        result = {"answer": answer}
        if observation is not None:
            observation.update(output={"answer_length": len(answer)})
        return result
