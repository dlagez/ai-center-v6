from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.db.session import get_db
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
