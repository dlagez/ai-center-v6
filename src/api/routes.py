from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from src.agents.sql.service import SqlAgentService
from src.api.schemas import (
    AgenticRagRequest,
    FileUploadResponse,
    IngestRequest,
    SearchRequest,
    SqlAgentRequest,
    SystemConfigCreateRequest,
    SystemConfigResponse,
    SystemConfigUpdateRequest,
    VideoInspectionRequest,
    VisionChatRequest,
)
from src.db.session import get_db
from src.media.service import VideoInspectionService
from src.models.llm import vision_completion
from src.observability import observe
from src.rag.agentic.service import AgenticRagService
from src.rag.service import KnowledgeIngestionService, KnowledgeSearchService
from src.repositories.system_config_repository import SystemConfigRepository
from src.services.system_config_service import SystemConfigService
from src.storage.file_service import get_file_service
from src.storage.minio_client import MinioConfigError
from src.api.excel_update_routes import router as excel_update_router

router = APIRouter()
router.include_router(excel_update_router)


@router.post("/files/upload", response_model=FileUploadResponse)
async def upload_file(file: UploadFile = File(...)) -> FileUploadResponse:
    try:
        with observe(
            name="api.files.upload",
            as_type="span",
            input={"file_name": file.filename},
        ):
            result = get_file_service().upload_file(file)
    except MinioConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"File upload failed: {exc}") from exc
    finally:
        await file.close()

    return FileUploadResponse(**result)


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


@router.post("/system-configs", response_model=SystemConfigResponse)
async def create_system_config(
    request: SystemConfigCreateRequest,
    db: Session = Depends(get_db),
) -> SystemConfigResponse:
    service = SystemConfigService(SystemConfigRepository(db))

    try:
        item = service.create_config(key=request.key, value=request.value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _to_system_config_response(item)


@router.get("/system-configs", response_model=list[SystemConfigResponse])
async def list_system_configs(db: Session = Depends(get_db)) -> list[SystemConfigResponse]:
    service = SystemConfigService(SystemConfigRepository(db))
    items = service.list_configs()
    return [_to_system_config_response(item) for item in items]


@router.get("/system-configs/{config_id}", response_model=SystemConfigResponse)
async def get_system_config(config_id: int, db: Session = Depends(get_db)) -> SystemConfigResponse:
    service = SystemConfigService(SystemConfigRepository(db))

    try:
        item = service.get_config(config_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return _to_system_config_response(item)


@router.put("/system-configs/{config_id}", response_model=SystemConfigResponse)
async def update_system_config(
    config_id: int,
    request: SystemConfigUpdateRequest,
    db: Session = Depends(get_db),
) -> SystemConfigResponse:
    service = SystemConfigService(SystemConfigRepository(db))

    try:
        item = service.update_config(config_id=config_id, value=request.value)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return _to_system_config_response(item)


@router.delete("/system-configs/{config_id}", status_code=204)
async def delete_system_config(config_id: int, db: Session = Depends(get_db)) -> None:
    service = SystemConfigService(SystemConfigRepository(db))

    try:
        service.delete_config(config_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


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


def _to_system_config_response(item) -> SystemConfigResponse:
    return SystemConfigResponse(
        id=item.id,
        key=item.key,
        value=item.value,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )
