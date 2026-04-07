from fastapi import APIRouter, HTTPException

from src.agents.sql.service import SqlAgentService
from src.api.schemas import (
    AgenticRagRequest,
    IngestRequest,
    SearchRequest,
    SqlAgentRequest,
    VideoInspectionRequest,
    VisionChatRequest,
)
from src.media.service import VideoInspectionService
from src.models.llm import vision_completion
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
                dialect=request.dialect,
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


@router.post("/models/vision/chat")
async def vision_chat(request: VisionChatRequest) -> dict:
    try:
        with observe(
            name="api.vision_chat",
            as_type="generation",
            input=request.model_dump(),
        ):
            answer = vision_completion(
                prompt=request.prompt,
                image_url=request.image_url,
                image_path=request.image_path,
                model=request.model,
                max_tokens=request.max_tokens,
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Vision chat failed: {exc}") from exc

    return {"answer": answer}


@router.post("/media/video/inspect")
async def inspect_video(request: VideoInspectionRequest) -> dict:
    service = VideoInspectionService()

    try:
        with observe(
            name="api.inspect_video",
            as_type="span",
            input=request.model_dump(),
        ):
            result = service.inspect_video(
                video_path=request.video_path,
                prompt=request.prompt,
                interval_seconds=request.interval_seconds,
                model=request.model,
                max_tokens=request.max_tokens,
                match_field=request.match_field,
                frames_dir=request.frames_dir,
                keep_frames=request.keep_frames,
                export_excel_path=request.export_excel_path,
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Video inspection failed: {exc}") from exc

    return result.model_dump()
