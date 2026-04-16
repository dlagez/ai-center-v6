from __future__ import annotations

from io import BytesIO

from fastapi import APIRouter, BackgroundTasks, File, Form, Query, Request, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

from src.workflow.excel_update.schemas import ApiErrorResponse, ApiSuccessResponse, CreateOperationRequest
from src.workflow.excel_update.services import ExcelUpdateAppService, ExcelUpdateError
from src.workflow.excel_update.utils import build_content_disposition
from src.workflow.excel_update.workers import OperationWorker

router = APIRouter(prefix="/api/excel-tasks", tags=["excel-update"])


@router.get("")
async def list_tasks(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    return _run(lambda service: service.list_tasks(page=page, page_size=page_size))


@router.post("/upload")
async def upload_task(
    file: UploadFile = File(...),
    task_name: str | None = Form(default=None),
    created_by: str | None = Form(default=None),
):
    try:
        payload = await file.read()
        response = _run(
            lambda service: service.upload_task(
                file_name=file.filename or "",
                payload=payload,
                task_name=task_name,
                created_by=created_by,
            )
        )
    finally:
        await file.close()
    return response


@router.get("/{task_id}")
async def get_task_detail(task_id: int):
    return _run(lambda service: service.get_task_detail(task_id))


@router.post("/{task_id}/operations")
async def create_operation(
    task_id: int,
    request: CreateOperationRequest,
    background_tasks: BackgroundTasks,
):
    response = _run(lambda service: service.create_operation(task_id, request))
    if not isinstance(response, JSONResponse):
        background_tasks.add_task(OperationWorker().process_pending_operations)
    return response


@router.get("/{task_id}/operations")
async def list_operations(
    task_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
):
    return _run(
        lambda service: service.list_operations(
            task_id=task_id,
            page=page,
            page_size=page_size,
            status=status,
        )
    )


@router.get("/{task_id}/operations/{operation_id}")
async def get_operation_detail(
    task_id: int,
    operation_id: int,
    request: Request,
    include_items: bool = Query(default=True),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=200),
):
    return _run(
        lambda service: service.get_operation_detail(
            task_id=task_id,
            operation_id=operation_id,
            include_items=include_items,
            page=page,
            page_size=page_size,
            base_url=str(request.base_url).rstrip("/"),
        )
    )


@router.get("/{task_id}/operations/{operation_id}/status")
async def get_operation_status(task_id: int, operation_id: int):
    return _run(lambda service: service.get_operation_status(task_id=task_id, operation_id=operation_id))


@router.get("/{task_id}/versions")
async def list_versions(
    task_id: int,
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    return _run(
        lambda service: service.list_versions(
            task_id=task_id,
            page=page,
            page_size=page_size,
            base_url=str(request.base_url).rstrip("/"),
        )
    )


@router.get("/{task_id}/download/latest")
async def get_latest_download(task_id: int, request: Request):
    return _run(
        lambda service: service.get_latest_download(
            task_id=task_id,
            base_url=str(request.base_url).rstrip("/"),
        )
    )


@router.get("/{task_id}/versions/{version_id}/download")
async def get_version_download(task_id: int, version_id: int, request: Request):
    return _run(
        lambda service: service.get_version_download(
            task_id=task_id,
            version_id=version_id,
            base_url=str(request.base_url).rstrip("/"),
        )
    )


@router.get("/{task_id}/download/original")
async def get_original_download(task_id: int, request: Request):
    return _run(
        lambda service: service.get_original_download(
            task_id=task_id,
            base_url=str(request.base_url).rstrip("/"),
        )
    )


@router.get("/files/{download_token}")
async def download_file(download_token: str):
    try:
        downloaded_file = ExcelUpdateAppService().get_downloaded_file(download_token)
    except ExcelUpdateError as exc:
        return JSONResponse(
            status_code=exc.http_status,
            content=ApiErrorResponse(code=exc.code, message=exc.message, error=exc.error).model_dump(),
        )
    return StreamingResponse(
        BytesIO(downloaded_file.content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": build_content_disposition(downloaded_file.file_name)},
    )


def _run(handler):
    try:
        data = handler(ExcelUpdateAppService())
    except ExcelUpdateError as exc:
        return JSONResponse(
            status_code=exc.http_status,
            content=ApiErrorResponse(code=exc.code, message=exc.message, error=exc.error).model_dump(),
        )
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=ApiErrorResponse(code=50000, message="system error", error={"reason": str(exc)}).model_dump(),
        )
    return ApiSuccessResponse(data=data).model_dump()
