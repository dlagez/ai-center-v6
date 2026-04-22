from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.knowledge.parser import DoclingBlockPreview, DoclingPagePreview
from src.repositories.uploaded_file_repository import UploadedFileRepository
from src.services.docling_pdf_service import DoclingPdfService

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

@router.post("/api/docling/pdf/parse", response_model=DoclingParseResponse)
async def parse_docling_pdf(
    request: DoclingParseRequest,
    db: Session = Depends(get_db),
) -> DoclingParseResponse:
    service = DoclingPdfService(UploadedFileRepository(db))

    try:
        parsed = service.parse_uploaded_pdf(request.file_id)
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
