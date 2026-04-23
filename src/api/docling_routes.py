from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.parser.parser import DoclingBlockPreview, DoclingPagePreview
from src.parser.service import DoclingParserService
from src.repositories.docling_parse_result_repository import DoclingParseResultRepository
from src.repositories.docling_parse_task_repository import DoclingParseTaskRepository
from src.repositories.uploaded_file_repository import UploadedFileRepository

router = APIRouter()


class DoclingParseRequest(BaseModel):
    file_id: str


class DoclingParseResponse(BaseModel):
    file_id: str
    file_name: str
    status: str
    error: str | None = None
    summary: dict
    pages: list[DoclingPagePreview]
    blocks: list[DoclingBlockPreview]
    result: dict | None = None


class DoclingTaskSummaryResponse(BaseModel):
    task_id: str
    file_id: str
    file_name: str
    status: str
    progress: float
    total_pages: int
    parsed_pages: int
    failed_pages: int
    batch_size: int
    current_batch_no: int
    parser_version: str
    error_message: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class DoclingTaskPageResultResponse(BaseModel):
    page_no: int
    batch_no: int
    parse_status: str
    block_count: int
    updated_at: str | None = None


class DoclingTaskFailedResultResponse(BaseModel):
    page_no: int
    batch_no: int
    parse_status: str
    error_message: str | None = None


class DoclingTaskDetailResponse(DoclingTaskSummaryResponse):
    failed_results: list[DoclingTaskFailedResultResponse]
    page_results: list[DoclingTaskPageResultResponse]

@router.post("/api/docling/pdf/parse", response_model=DoclingParseResponse)
async def parse_docling_pdf(
    request: DoclingParseRequest,
    db: Session = Depends(get_db),
) -> DoclingParseResponse:
    service = DoclingParserService(
        UploadedFileRepository(db),
        DoclingParseTaskRepository(db),
        DoclingParseResultRepository(db),
    )

    try:
        parsed = service.parse_pdf_file(request.file_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return DoclingParseResponse(
        file_id=parsed.file_id,
        file_name=parsed.file_name,
        status=parsed.status,
        error=parsed.error,
        summary=parsed.summary,
        pages=parsed.pages,
        blocks=parsed.blocks,
        result=parsed.result,
    )


@router.get("/api/docling/pdf/tasks", response_model=list[DoclingTaskSummaryResponse])
async def list_docling_tasks(
    file_id: str | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
) -> list[DoclingTaskSummaryResponse]:
    service = DoclingParserService(
        UploadedFileRepository(db),
        DoclingParseTaskRepository(db),
        DoclingParseResultRepository(db),
    )
    tasks = service.list_tasks(file_id=file_id, limit=limit)
    return [
        DoclingTaskSummaryResponse(
            task_id=item.task_id,
            file_id=item.file_id,
            file_name=item.file_name,
            status=item.status,
            progress=item.progress,
            total_pages=item.total_pages,
            parsed_pages=item.parsed_pages,
            failed_pages=item.failed_pages,
            batch_size=item.batch_size,
            current_batch_no=item.current_batch_no,
            parser_version=item.parser_version,
            error_message=item.error_message,
            started_at=item.started_at.isoformat() if item.started_at else None,
            finished_at=item.finished_at.isoformat() if item.finished_at else None,
            created_at=item.created_at.isoformat() if item.created_at else None,
            updated_at=item.updated_at.isoformat() if item.updated_at else None,
        )
        for item in tasks
    ]


@router.get("/api/docling/pdf/tasks/{task_id}", response_model=DoclingTaskDetailResponse)
async def get_docling_task_detail(
    task_id: str,
    db: Session = Depends(get_db),
) -> DoclingTaskDetailResponse:
    service = DoclingParserService(
        UploadedFileRepository(db),
        DoclingParseTaskRepository(db),
        DoclingParseResultRepository(db),
    )
    try:
        task = service.get_task_detail(task_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return DoclingTaskDetailResponse(
        task_id=task.task_id,
        file_id=task.file_id,
        file_name=task.file_name,
        status=task.status,
        progress=task.progress,
        total_pages=task.total_pages,
        parsed_pages=task.parsed_pages,
        failed_pages=task.failed_pages,
        batch_size=task.batch_size,
        current_batch_no=task.current_batch_no,
        parser_version=task.parser_version,
        error_message=task.error_message,
        started_at=task.started_at.isoformat() if task.started_at else None,
        finished_at=task.finished_at.isoformat() if task.finished_at else None,
        created_at=task.created_at.isoformat() if task.created_at else None,
        updated_at=task.updated_at.isoformat() if task.updated_at else None,
        failed_results=[
            DoclingTaskFailedResultResponse(**item)
            for item in task.failed_results
        ],
        page_results=[
            DoclingTaskPageResultResponse(
                page_no=item["page_no"],
                batch_no=item["batch_no"],
                parse_status=item["parse_status"],
                block_count=item["block_count"],
                updated_at=item["updated_at"].isoformat() if item["updated_at"] else None,
            )
            for item in task.page_results
        ],
    )
