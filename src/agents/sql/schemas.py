from typing import Any

from pydantic import BaseModel, Field
from typing_extensions import TypedDict


class SqlAgentOutput(BaseModel):
    question: str
    dialect: str
    db_path: str
    sql_query: str = ""
    rows: list[dict[str, Any]] = Field(default_factory=list)
    answer: str = ""
    error: str | None = None
    trace_id: str | None = None
    trace_url: str | None = None


class SqlAgentState(TypedDict, total=False):
    question: str
    dialect: str
    db_path: str
    mysql_config: dict[str, Any]
    max_rows: int
    max_retries: int
    retry_count: int
    table_names: list[str]
    selected_tables: list[str]
    schema: dict[str, str]
    schema_text: str
    sql_query: str
    query_result: list[dict[str, Any]]
    query_error: str | None
    answer: str
