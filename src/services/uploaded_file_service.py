from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from src.api.schemas import FileUploadResponse, PdfPreviewFileResponse
from src.db.models.uploaded_file import UploadedFile
from src.repositories.uploaded_file_repository import UploadedFileRepository
from src.config.settings import settings
from src.storage.file_service import get_file_service


class UploadedFileService:
    def __init__(self, repository: UploadedFileRepository) -> None:
        self.repository = repository

    def upload(
        self,
        file: UploadFile,
        *,
        biz_type: str = "general",
        biz_id: str | None = None,
    ) -> FileUploadResponse:
        original_name = Path(file.filename or "file").name
        stored_name = f"{uuid4().hex}_{original_name}"
        date_folder = datetime.now().strftime("%Y-%m-%d")
        folder_path = f"{biz_type}/{date_folder}"
        object_name = f"{folder_path}/{stored_name}"

        result = get_file_service().upload_file(file, object_name=object_name)
        payload_size = self._resolve_file_size(file)
        content_type = (
            file.content_type
            or "application/octet-stream"
        )
        entity = UploadedFile(
            file_id=uuid4().hex,
            file_name=original_name,
            stored_name=stored_name,
            object_name=result["object_name"],
            bucket_name=settings.minio_bucket or "",
            biz_type=biz_type,
            date_folder=date_folder,
            folder_path=folder_path,
            content_type=content_type,
            file_size=payload_size,
            file_ext=Path(original_name).suffix.lower().lstrip(".") or None,
            biz_id=biz_id,
        )
        created = self.repository.create(entity)
        return FileUploadResponse(
            file_id=created.file_id,
            file_name=created.file_name,
            content_type=created.content_type,
            file_size=created.file_size,
            biz_type=created.biz_type,
            folder_path=created.folder_path,
            object_name=result["object_name"],
            url=result["url"],
            etag=result["etag"],
        )

    def list_pdf_files(self) -> list[PdfPreviewFileResponse]:
        return [self._to_pdf_response(item) for item in self.repository.list_pdf_files()]

    def get_pdf_file(self, file_id: str) -> PdfPreviewFileResponse:
        entity = self.repository.get_by_file_id(file_id)
        if entity is None or entity.status != "active" or entity.content_type != "application/pdf":
            raise ValueError("PDF file not found")
        return self._to_pdf_response(entity)

    @staticmethod
    def _resolve_file_size(file: UploadFile) -> int:
        stream = getattr(file, "file", None)
        if stream is None or not hasattr(stream, "seek") or not hasattr(stream, "tell"):
            return 0
        current_position = stream.tell()
        stream.seek(0, 2)
        file_size = stream.tell()
        stream.seek(current_position)
        return file_size

    @staticmethod
    def _to_pdf_response(entity: UploadedFile) -> PdfPreviewFileResponse:
        return PdfPreviewFileResponse(
            file_id=entity.file_id,
            file_name=entity.file_name,
            stored_name=entity.stored_name,
            object_name=entity.object_name,
            bucket_name=entity.bucket_name,
            biz_type=entity.biz_type,
            date_folder=entity.date_folder,
            folder_path=entity.folder_path,
            content_type=entity.content_type,
            file_size=entity.file_size,
            file_ext=entity.file_ext,
            created_at=entity.created_at,
        )
