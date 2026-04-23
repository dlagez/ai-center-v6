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


class FileManagerDetailResponse(BaseModel):
    file: FileManagerItemResponse


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
    db: Session = Depends(get_db),
) -> FileManagerDetailResponse:
    file_repository = UploadedFileRepository(db)
    file_entity = file_repository.get_by_file_id(file_id)
    if file_entity is None or file_entity.status != "active":
        raise HTTPException(status_code=404, detail="File not found")

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
    )
