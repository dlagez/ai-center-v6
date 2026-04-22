from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from src.api.schemas import PdfPreviewFileResponse
from src.db.session import get_db
from src.repositories.uploaded_file_repository import UploadedFileRepository
from src.services.uploaded_file_service import UploadedFileService
from src.storage.file_service import get_file_service

router = APIRouter()


def _build_inline_pdf_headers(filename: str) -> dict[str, str]:
    safe_name = Path(filename or "document.pdf").name
    ascii_fallback = safe_name.encode("ascii", "ignore").decode("ascii").strip() or "document.pdf"
    ascii_fallback = ascii_fallback.replace("\\", "_").replace('"', "_")
    encoded_name = quote(safe_name, safe="")
    return {
        "Content-Disposition": (
            f'inline; filename="{ascii_fallback}"; filename*=UTF-8\'\'{encoded_name}'
        )
    }


@router.get("/api/pdf-preview/files", response_model=list[PdfPreviewFileResponse])
async def list_pdf_preview_files(db: Session = Depends(get_db)) -> list[PdfPreviewFileResponse]:
    service = UploadedFileService(UploadedFileRepository(db))
    return service.list_pdf_files()


@router.get("/api/pdf-preview/files/{file_id}", response_model=PdfPreviewFileResponse)
async def get_pdf_preview_file(
    file_id: str,
    db: Session = Depends(get_db),
) -> PdfPreviewFileResponse:
    service = UploadedFileService(UploadedFileRepository(db))
    try:
        return service.get_pdf_file(file_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/api/pdf-preview/files/{file_id}/file")
async def stream_pdf_preview_file(file_id: str, db: Session = Depends(get_db)) -> Response:
    service = UploadedFileService(UploadedFileRepository(db))
    try:
        file_record = service.get_pdf_file(file_id)
        payload = get_file_service().download_file(file_record.object_name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to stream PDF: {exc}") from exc

    headers = _build_inline_pdf_headers(file_record.file_name)
    return Response(content=payload, media_type="application/pdf", headers=headers)
