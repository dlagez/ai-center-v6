import json
import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from src.agents.sql.service import SqlAgentService
from src.api.schemas import (
    AgenticRagRequest,
    IngestRequest,
    SearchRequest,
    SqlAgentRequest,
    VideoInspectionRequest,
    VisionChatRequest,
)
from src.config.settings import settings
from src.media.service import VideoInspectionService
from src.models.llm import vision_completion
from src.observability import observe
from src.rag.agentic.service import AgenticRagService
from src.rag.service import KnowledgeIngestionService, KnowledgeSearchService
from src.workflow.excel_update.analyzer import analyze_excel_update
from src.workflow.excel_update.schemas import ExcelUpdateRequest
from src.workflow.excel_update.task_service import ExcelUpdateTaskService

router = APIRouter()


def _parse_json_form_field(value: str | None, field_name: str) -> list[dict]:
    if not value:
        return []

    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{field_name} must be valid JSON") from exc

    if not isinstance(parsed, list):
        raise ValueError(f"{field_name} must be a JSON array")
    return parsed


async def _save_uploaded_excel(file: UploadFile) -> tuple[str, str]:
    original_name = file.filename or "uploaded.xlsx"
    uploads_dir = Path(settings.excel_update_output_dir).expanduser().resolve() / "_uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)

    suffix = Path(original_name).suffix or ".xlsx"
    saved_path = uploads_dir / f"{uuid4().hex}{suffix}"
    with saved_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    await file.close()

    return str(saved_path), original_name


@router.get("/pages/excel-update")
async def excel_update_page() -> FileResponse:
    page_path = Path(__file__).resolve().parent / "static" / "excel-update.html"
    if not page_path.is_file():
        raise HTTPException(status_code=404, detail="Excel update page not found")
    return FileResponse(path=page_path, media_type="text/html; charset=utf-8")


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


@router.post("/workflow/excel-update/tasks")
async def create_excel_update_task(
    file: UploadFile = File(...),
    user_prompt: str | None = Form(default=None),
    sheet_name: str | None = Form(default=None),
    match_column: str | None = Form(default=None),
    match_field: str | None = Form(default=None),
    target_column: str | None = Form(default=None),
    query_conditions: str | None = Form(default=None),
    overwrite_existing: bool = Form(default=True),
    operator: str | None = Form(default=None),
) -> dict:
    task_service = ExcelUpdateTaskService()

    try:
        saved_excel_path, original_name = await _save_uploaded_excel(file)
        parsed_query_conditions = _parse_json_form_field(query_conditions, "query_conditions")
        analysis = None
        if user_prompt and (not sheet_name or not match_column or not match_field or not target_column or not parsed_query_conditions):
            analysis = analyze_excel_update(saved_excel_path, user_prompt)

        resolved_target_column = target_column or (analysis.target_column if analysis else None)
        if not resolved_target_column:
            raise ValueError("target_column is required unless it can be inferred from user_prompt")

        request = ExcelUpdateRequest(
            excel_path=saved_excel_path,
            user_prompt=user_prompt,
            sheet_name=sheet_name or (analysis.sheet_name if analysis else None),
            match_column=match_column or (analysis.match_column if analysis else "项目编号"),
            match_field=match_field or (analysis.match_field if analysis else "project_no"),
            target_column=resolved_target_column,
            query_conditions=parsed_query_conditions or (analysis.query_conditions if analysis else []),
            overwrite_existing=overwrite_existing,
            operator=operator,
        )
        with observe(
            name="api.excel_update.create_task",
            as_type="span",
            input={
                "file_name": original_name,
                "user_prompt": user_prompt,
                "sheet_name": sheet_name,
                "match_column": match_column,
                "match_field": match_field,
                "target_column": resolved_target_column,
                "query_conditions": query_conditions,
                "overwrite_existing": overwrite_existing,
                "operator": operator,
            },
        ):
            result = task_service.create_task(request=request, uploaded_file_name=original_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Excel update failed: {exc}") from exc

    return result.model_dump()


@router.post("/workflow/excel-update/analysis")
async def analyze_excel_update_task(
    file: UploadFile = File(...),
    user_prompt: str = Form(...),
) -> dict:
    try:
        saved_excel_path, _ = await _save_uploaded_excel(file)
        with observe(
            name="api.excel_update.analysis",
            as_type="generation",
            input={"excel_path": saved_excel_path, "user_prompt": user_prompt},
        ):
            result = analyze_excel_update(saved_excel_path, user_prompt)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Excel analysis failed: {exc}") from exc

    return result.model_dump(mode="json")


@router.get("/workflow/excel-update/tasks/{task_id}")
async def get_excel_update_task(task_id: str) -> dict:
    task_service = ExcelUpdateTaskService()

    try:
        with observe(
            name="api.excel_update.get_task",
            as_type="span",
            input={"task_id": task_id},
        ):
            result = task_service.get_task(task_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Excel update task lookup failed: {exc}") from exc

    return result.model_dump()


@router.get("/workflow/excel-update/tasks/{task_id}/file")
async def download_excel_update_file(task_id: str) -> FileResponse:
    task_service = ExcelUpdateTaskService()

    try:
        with observe(
            name="api.excel_update.download_file",
            as_type="span",
            input={"task_id": task_id},
        ):
            task = task_service.get_task(task_id)
            output_path = task_service.get_output_file_path(task_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Excel update file download failed: {exc}") from exc

    return FileResponse(
        path=output_path,
        filename=task.output_file_name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
