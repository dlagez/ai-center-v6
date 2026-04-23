from datetime import datetime
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.repositories.docling_parse_result_repository import DoclingParseResultRepository
from src.repositories.docling_parse_task_repository import DoclingParseTaskRepository
from src.repositories.uploaded_file_repository import UploadedFileRepository
from src.services.uploaded_file_service import UploadedFileService

router = APIRouter()


class FileManagerItemResponse(BaseModel):
    file_id: str
    file_name: str
    stored_name: str
    object_name: str
    bucket_name: str
    biz_type: str
    date_folder: str
    folder_path: str
    content_type: str
    file_size: int
    file_ext: str | None
    created_at: datetime


class FileManagerDeleteResponse(BaseModel):
    file_id: str
    file_name: str


class FileManagerParseTaskResponse(BaseModel):
    id: int
    task_id: str
    status: str
    parser_version: str
    batch_size: int
    current_batch_no: int
    total_pages: int
    parsed_pages: int
    failed_pages: int
    progress: float
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime


class FileManagerParsePageResponse(BaseModel):
    id: int
    result_id: str
    page_no: int
    batch_no: int
    parse_status: str
    block_count: int
    error_message: str | None
    markdown: str | None
    result_json: dict | None
    created_at: datetime
    updated_at: datetime


class FileManagerDetailResponse(BaseModel):
    file: FileManagerItemResponse
    parse_tasks: list[FileManagerParseTaskResponse]
    selected_task: FileManagerParseTaskResponse | None
    page_results: list[FileManagerParsePageResponse]


def _build_service(db: Session) -> UploadedFileService:
    return UploadedFileService(UploadedFileRepository(db))


@router.get("/api/files", response_model=list[FileManagerItemResponse])
async def list_files(
    biz_type: str | None = Query(default=None),
    limit: int = Query(default=500, ge=1, le=2000),
    db: Session = Depends(get_db),
) -> list[FileManagerItemResponse]:
    service = _build_service(db)
    return [FileManagerItemResponse(**item) for item in service.list_files(biz_type=biz_type, limit=limit)]


@router.delete("/api/files/{file_id}", response_model=FileManagerDeleteResponse)
async def delete_file(file_id: str, db: Session = Depends(get_db)) -> FileManagerDeleteResponse:
    service = _build_service(db)
    try:
        result = service.delete_file(file_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FileManagerDeleteResponse(**result)


@router.get("/api/files/{file_id}", response_model=FileManagerDetailResponse)
async def get_file_detail(
    file_id: str,
    task_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> FileManagerDetailResponse:
    file_repository = UploadedFileRepository(db)
    file_entity = file_repository.get_by_file_id(file_id)
    if file_entity is None or file_entity.status != "active":
        raise HTTPException(status_code=404, detail="File not found")

    task_repository = DoclingParseTaskRepository(db)
    result_repository = DoclingParseResultRepository(db)
    tasks = task_repository.list_recent(file_id=file_id, limit=100)
    selected_task = None
    if task_id:
        selected_task = next((item for item in tasks if item.task_id == task_id), None)
        if selected_task is None:
            raise HTTPException(status_code=404, detail="Parse task not found")
    elif tasks:
        selected_task = tasks[0]

    page_results = result_repository.list_by_task_id(selected_task.task_id) if selected_task else []

    return FileManagerDetailResponse(
        file=FileManagerItemResponse(
            file_id=file_entity.file_id,
            file_name=file_entity.file_name,
            stored_name=file_entity.stored_name,
            object_name=file_entity.object_name,
            bucket_name=file_entity.bucket_name,
            biz_type=file_entity.biz_type,
            date_folder=file_entity.date_folder,
            folder_path=file_entity.folder_path,
            content_type=file_entity.content_type,
            file_size=file_entity.file_size,
            file_ext=file_entity.file_ext,
            created_at=file_entity.created_at,
        ),
        parse_tasks=[
            FileManagerParseTaskResponse(
                id=item.id,
                task_id=item.task_id,
                status=item.status,
                parser_version=item.parser_version,
                batch_size=item.batch_size,
                current_batch_no=item.current_batch_no,
                total_pages=item.total_pages,
                parsed_pages=item.parsed_pages,
                failed_pages=item.failed_pages,
                progress=float(item.progress) if item.progress is not None else 0.0,
                error_message=item.error_message,
                started_at=item.started_at,
                finished_at=item.finished_at,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
            for item in tasks
        ],
        selected_task=(
            FileManagerParseTaskResponse(
                id=selected_task.id,
                task_id=selected_task.task_id,
                status=selected_task.status,
                parser_version=selected_task.parser_version,
                batch_size=selected_task.batch_size,
                current_batch_no=selected_task.current_batch_no,
                total_pages=selected_task.total_pages,
                parsed_pages=selected_task.parsed_pages,
                failed_pages=selected_task.failed_pages,
                progress=float(selected_task.progress) if selected_task.progress is not None else 0.0,
                error_message=selected_task.error_message,
                started_at=selected_task.started_at,
                finished_at=selected_task.finished_at,
                created_at=selected_task.created_at,
                updated_at=selected_task.updated_at,
            )
            if selected_task
            else None
        ),
        page_results=[
            FileManagerParsePageResponse(
                id=item.id,
                result_id=item.result_id,
                page_no=item.page_no,
                batch_no=item.batch_no,
                parse_status=item.parse_status,
                block_count=item.block_count,
                error_message=item.error_message,
                markdown=item.markdown,
                result_json=json.loads(item.result_json) if item.result_json else None,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
            for item in page_results
        ],
    )
