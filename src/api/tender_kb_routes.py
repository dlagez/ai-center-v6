from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.repositories.docling_parse_result_repository import DoclingParseResultRepository
from src.repositories.docling_parse_task_repository import DoclingParseTaskRepository
from src.repositories.uploaded_file_repository import UploadedFileRepository
from src.services.tender_kb_service import TenderKbService

router = APIRouter()


class TenderKbIndexRequest(BaseModel):
    file_id: str


class TenderKbIndexResponse(BaseModel):
    file_id: str
    file_name: str
    parse_status: str
    chunk_count: int
    collection_name: str
    pages: int


class TenderKbAskRequest(BaseModel):
    file_id: str
    question: str = Field(..., min_length=1)
    limit: int = Field(default=5, ge=1, le=20)


class TenderKbAskSourceResponse(BaseModel):
    id: str
    score: float
    text: str
    headers: list[str]
    metadata: dict


class TenderKbAskResponse(BaseModel):
    file_id: str
    file_name: str
    question: str
    answer: str
    sources: list[TenderKbAskSourceResponse]


@router.post("/api/tender-kb/index", response_model=TenderKbIndexResponse)
async def index_tender_kb(
    request: TenderKbIndexRequest,
    db: Session = Depends(get_db),
) -> TenderKbIndexResponse:
    service = TenderKbService(
        UploadedFileRepository(db),
        DoclingParseTaskRepository(db),
        DoclingParseResultRepository(db),
    )
    try:
        result = service.index_file(request.file_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return TenderKbIndexResponse(**result)


@router.post("/api/tender-kb/ask", response_model=TenderKbAskResponse)
async def ask_tender_kb(
    request: TenderKbAskRequest,
    db: Session = Depends(get_db),
) -> TenderKbAskResponse:
    service = TenderKbService(
        UploadedFileRepository(db),
        DoclingParseTaskRepository(db),
        DoclingParseResultRepository(db),
    )
    try:
        result = service.ask(
            file_id=request.file_id,
            question=request.question,
            limit=request.limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return TenderKbAskResponse(
        file_id=result["file_id"],
        file_name=result["file_name"],
        question=result["question"],
        answer=result["answer"],
        sources=[TenderKbAskSourceResponse(**item) for item in result["sources"]],
    )
