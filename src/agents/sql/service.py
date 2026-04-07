from pathlib import Path

from src.agents.sql.db import ensure_db_file
from src.agents.sql.graph import build_sql_agent_graph
from src.agents.sql.schemas import SqlAgentOutput
from src.config.settings import settings
from src.observability import current_trace_info, observe


class SqlAgentService:
    def __init__(self, graph=None) -> None:
        self.graph = graph or build_sql_agent_graph()

    def answer(
        self,
        question: str,
        db_path: str | Path | None = None,
        max_rows: int | None = None,
    ) -> SqlAgentOutput:
        question_text = question.strip()
        if not question_text:
            raise ValueError("Question must not be empty")

        resolved_db_path_value = db_path or settings.sql_agent_default_db_path
        if not resolved_db_path_value:
            raise ValueError("Database path must be provided")

        resolved_db_path = ensure_db_file(resolved_db_path_value)

        resolved_max_rows = max_rows or settings.sql_agent_max_rows
        if resolved_max_rows <= 0:
            raise ValueError("max_rows must be greater than 0")

        with observe(
            name="sql_agent.answer",
            as_type="agent",
            input={
                "question": question_text,
                "db_path": str(resolved_db_path),
                "max_rows": resolved_max_rows,
            },
        ) as observation:
            result = self.graph.invoke(
                {
                    "question": question_text,
                    "db_path": str(resolved_db_path),
                    "max_rows": resolved_max_rows,
                    "max_retries": settings.sql_agent_max_retries,
                }
            )
            trace_id, trace_url = current_trace_info()
            output = SqlAgentOutput(
                question=question_text,
                db_path=str(resolved_db_path),
                sql_query=result.get("sql_query", ""),
                rows=result.get("query_result", []),
                answer=result.get("answer", ""),
                error=result.get("query_error"),
                trace_id=trace_id,
                trace_url=trace_url,
            )
            if observation is not None:
                observation.update(
                    output={
                        "sql_query": output.sql_query,
                        "row_count": len(output.rows),
                        "error": output.error,
                    }
                )
            return output
