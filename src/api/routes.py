import json
from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import quote
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from src.agents.sql.service import SqlAgentService
from src.api.schemas import (
    AgenticRagRequest,
    FileUploadResponse,
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
from src.rag.service import KnowledgeSearchService
from src.repositories.system_config_repository import SystemConfigRepository
from src.repositories.uploaded_file_repository import UploadedFileRepository
from src.services.system_config_service import SystemConfigService
from src.services.uploaded_file_service import UploadedFileService
from src.storage.file_service import get_file_service
from src.storage.minio_client import MinioConfigError
from src.workflow.excel_update.analyzer import analyze_excel_update
from src.workflow.excel_update.schemas import ExcelUpdateOperationCreate
from src.workflow.excel_update.task_service import ExcelUpdateTaskService

router = APIRouter()


def _build_download_headers(filename: str) -> dict[str, str]:
    safe_name = Path(filename or "file.xlsx").name
    ascii_fallback = safe_name.encode("ascii", "ignore").decode("ascii").strip()
    if not ascii_fallback:
        ascii_fallback = "file.xlsx"
    ascii_fallback = ascii_fallback.replace("\\", "_").replace('"', "_")
    encoded_name = quote(safe_name, safe="")
    return {
        "Content-Disposition": (
            f'attachment; filename="{ascii_fallback}"; filename*=UTF-8\'\'{encoded_name}'
        )
    }


def _to_system_config_response(item) -> SystemConfigResponse:
    return SystemConfigResponse(
        id=item.id,
        key=item.key,
        value=item.value,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


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
    object_name = f"excel-update/uploads/{uuid4().hex}_{Path(original_name).name}"
    result = get_file_service().upload_file(file, object_name=object_name)
    await file.close()
    return result["object_name"], original_name


async def _save_optional_uploaded_excel(file: UploadFile | None) -> tuple[str | None, str | None]:
    if file is None:
        return None, None
    return await _save_uploaded_excel(file)


def _download_excel_to_tempfile(object_name: str, suffix: str = ".xlsx") -> str:
    payload = get_file_service().download_file(object_name)
    temp_file = NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        temp_file.write(payload)
        temp_file.flush()
    finally:
        temp_file.close()
    return temp_file.name


@router.post("/files/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    biz_type: str = Form(default="general"),
    biz_id: str | None = Form(default=None),
    db: Session = Depends(get_db),
) -> FileUploadResponse:
    service = UploadedFileService(UploadedFileRepository(db))
    try:
        with observe(
            name="api.files.upload",
            as_type="span",
            input={"file_name": file.filename},
        ):
            result = service.upload(file, biz_type=biz_type, biz_id=biz_id)
    except MinioConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"File upload failed: {exc}") from exc
    finally:
        await file.close()

    return result


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
async def create_excel_update_task(file: UploadFile = File(...)) -> dict:
    task_service = ExcelUpdateTaskService()

    try:
        saved_excel_path, original_name = await _save_uploaded_excel(file)
        with observe(
            name="api.excel_update.create_task",
            as_type="span",
            input={"file_name": original_name},
        ):
            result = task_service.create_task(
                source_excel_path=saved_excel_path,
                uploaded_file_name=original_name,
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Excel update failed: {exc}") from exc

    return result.model_dump(mode="json")


@router.get("/workflow/excel-update/tasks")
async def list_excel_update_tasks() -> list[dict]:
    task_service = ExcelUpdateTaskService()

    try:
        with observe(
            name="api.excel_update.list_tasks",
            as_type="span",
            input={},
        ):
            result = task_service.list_tasks()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Excel update task list failed: {exc}") from exc

    return [item.model_dump(mode="json") for item in result]


@router.post("/workflow/excel-update/tasks/{task_id}/operations")
async def create_excel_update_operation(
    task_id: str,
    source_type: str = Form(default="pm_api"),
    source_file: UploadFile | None = File(default=None),
    user_prompt: str | None = Form(default=None),
    sheet_name: str | None = Form(default=None),
    match_column: str | None = Form(default=None),
    match_field: str | None = Form(default=None),
    source_sheet_name: str | None = Form(default=None),
    source_value_column: str | None = Form(default=None),
    target_column: str | None = Form(default=None),
    query_conditions: str | None = Form(default=None),
    overwrite_existing: bool = Form(default=True),
    operator: str | None = Form(default=None),
) -> dict:
    task_service = ExcelUpdateTaskService()

    try:
        parsed_query_conditions = _parse_json_form_field(query_conditions, "query_conditions")
        source_excel_path, _ = await _save_optional_uploaded_excel(source_file)
        operation = ExcelUpdateOperationCreate(
            source_type=source_type,
            user_prompt=user_prompt,
            sheet_name=sheet_name,
            match_column=match_column,
            match_field=match_field,
            source_excel_path=source_excel_path,
            source_sheet_name=source_sheet_name,
            source_value_column=source_value_column,
            target_column=target_column,
            query_conditions=parsed_query_conditions,
            overwrite_existing=overwrite_existing,
            operator=operator,
        )
        with observe(
            name="api.excel_update.create_operation",
            as_type="span",
            input={
                "task_id": task_id,
                "source_type": source_type,
                "user_prompt": user_prompt,
                "sheet_name": sheet_name,
                "match_column": match_column,
                "match_field": match_field,
                "source_sheet_name": source_sheet_name,
                "source_value_column": source_value_column,
                "target_column": target_column,
                "query_conditions": query_conditions,
                "overwrite_existing": overwrite_existing,
                "operator": operator,
            },
        ):
            result = task_service.run_operation(task_id=task_id, operation=operation)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Excel update operation failed: {exc}") from exc

    return result.model_dump(mode="json")


@router.post("/workflow/excel-update/analysis")
async def analyze_excel_update_task(
    file: UploadFile = File(...),
    user_prompt: str = Form(...),
) -> dict:
    temp_path: str | None = None
    try:
        saved_excel_path, _ = await _save_uploaded_excel(file)
        temp_path = _download_excel_to_tempfile(saved_excel_path)
        with observe(
            name="api.excel_update.analysis",
            as_type="generation",
            input={"excel_path": saved_excel_path, "user_prompt": user_prompt},
        ):
            result = analyze_excel_update(temp_path, user_prompt)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Excel analysis failed: {exc}") from exc
    finally:
        if temp_path:
            Path(temp_path).unlink(missing_ok=True)

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

    return result.model_dump(mode="json")


@router.get("/workflow/excel-update/tasks/{task_id}/file")
async def download_excel_update_file(task_id: str) -> StreamingResponse:
    task_service = ExcelUpdateTaskService()

    try:
        with observe(
            name="api.excel_update.download_file",
            as_type="span",
            input={"task_id": task_id},
        ):
            task = task_service.get_task(task_id)
            payload = task_service.get_output_file_content(task_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Excel update file download failed: {exc}") from exc

    return StreamingResponse(
        BytesIO(payload),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=_build_download_headers(task.latest_output_file_name),
    )


@router.get("/workflow/excel-update/tasks/{task_id}/operations/{operation_id}/file")
async def download_excel_update_operation_file(task_id: str, operation_id: str) -> StreamingResponse:
    task_service = ExcelUpdateTaskService()

    try:
        with observe(
            name="api.excel_update.download_operation_file",
            as_type="span",
            input={"task_id": task_id, "operation_id": operation_id},
        ):
            task = task_service.get_task(task_id)
            operation = next((item for item in task.operations if item.operation_id == operation_id), None)
            if operation is None:
                raise FileNotFoundError(f"Excel update operation not found: {operation_id}")
            payload = task_service.get_operation_output_file_content(task_id, operation_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Excel update operation file download failed: {exc}") from exc

    return StreamingResponse(
        BytesIO(payload),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=_build_download_headers(operation.output_file_name),
    )
