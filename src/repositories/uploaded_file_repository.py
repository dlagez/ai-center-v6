from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from src.db.models.uploaded_file import UploadedFile


class UploadedFileRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, entity: UploadedFile) -> UploadedFile:
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def get_by_file_id(self, file_id: str) -> UploadedFile | None:
        statement = select(UploadedFile).where(UploadedFile.file_id == file_id)
        return self.db.execute(statement).scalar_one_or_none()

    def list_pdf_files(self) -> list[UploadedFile]:
        statement = (
            select(UploadedFile)
            .where(
                UploadedFile.status == "active",
                UploadedFile.content_type == "application/pdf",
            )
            .order_by(desc(UploadedFile.created_at), desc(UploadedFile.id))
        )
        return list(self.db.execute(statement).scalars().all())
