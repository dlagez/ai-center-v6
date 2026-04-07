from pathlib import Path

from src.agents.sql.db import ensure_db_file, resolve_mysql_config
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
        dialect: str | None = None,
        db_path: str | Path | None = None,
        max_rows: int | None = None,
    ) -> SqlAgentOutput:
        question_text = question.strip()
        if not question_text:
            raise ValueError("Question must not be empty")

        resolved_dialect = (dialect or settings.sql_agent_dialect or "sqlite").strip().lower()
        if resolved_dialect not in {"sqlite", "mysql"}:
            raise ValueError("dialect must be either 'sqlite' or 'mysql'")

        mysql_config: dict[str, str | int] = {}
        if resolved_dialect == "mysql":
            mysql_config = resolve_mysql_config(
                {
                    "host": settings.sql_agent_mysql_host,
                    "port": settings.sql_agent_mysql_port,
                    "user": settings.sql_agent_mysql_user,
                    "password": settings.sql_agent_mysql_password,
                    "database": settings.sql_agent_mysql_database,
                }
            )
            resolved_db_path = f"{mysql_config['host']}:{mysql_config['port']}/{mysql_config['database']}"
        else:
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
                "dialect": resolved_dialect,
                "db_path": str(resolved_db_path),
                "max_rows": resolved_max_rows,
            },
        ) as observation:
            result = self.graph.invoke(
                {
                    "question": question_text,
                    "dialect": resolved_dialect,
                    "db_path": str(resolved_db_path),
                    "mysql_config": mysql_config,
                    "max_rows": resolved_max_rows,
                    "max_retries": settings.sql_agent_max_retries,
                }
            )
            trace_id, trace_url = current_trace_info()
            output = SqlAgentOutput(
                question=question_text,
                dialect=resolved_dialect,
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
