from fastapi import APIRouter, HTTPException

from src.agents.sql.service import SqlAgentService
from src.api.schemas import AgenticRagRequest, IngestRequest, SearchRequest, SqlAgentRequest
from src.observability import observe
from src.rag.agentic.service import AgenticRagService
from src.rag.service import KnowledgeIngestionService, KnowledgeSearchService

router = APIRouter()


@router.post("/agents/sql")
async def sql_agent_answer(request: SqlAgentRequest) -> dict:
    service = SqlAgentService()

    try:
        with observe(
            name="api.sql_agent_answer",
            as_type="span",
            input=request.model_dump(),
        ):
            result = service.answer(
                question=request.question,
                db_path=request.db_path,
                max_rows=request.max_rows,
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"SQL agent failed: {exc}") from exc

    return result.model_dump()


@router.post("/knowledge/ingest")
async def ingest_knowledge(request: IngestRequest) -> dict:
    service = KnowledgeIngestionService()

    try:
        with observe(
            name="api.ingest_knowledge",
            as_type="span",
            input=request.model_dump(),
        ):
            result = service.ingest_path(source=request.source)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Knowledge ingestion failed: {exc}") from exc

    return result.model_dump()


@router.post("/knowledge/search")
async def search_knowledge(request: SearchRequest) -> dict:
    service = KnowledgeSearchService()

    try:
        with observe(
            name="api.search_knowledge",
            as_type="span",
            input=request.model_dump(),
        ):
            result = service.search(query=request.query, limit=request.limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Knowledge search failed: {exc}") from exc

    return result.model_dump()


@router.post("/rag/agentic-answer")
async def agentic_rag_answer(request: AgenticRagRequest) -> dict:
    service = AgenticRagService()

    try:
        with observe(
            name="api.agentic_rag_answer",
            as_type="span",
            input=request.model_dump(),
        ):
            result = service.answer(question=request.question, limit=request.limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Agentic RAG failed: {exc}") from exc

    return result.model_dump()
