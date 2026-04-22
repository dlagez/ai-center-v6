from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models.docling_parse_result import DoclingParseResult


class DoclingParseResultRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_file_id(self, file_id: str) -> DoclingParseResult | None:
        statement = select(DoclingParseResult).where(DoclingParseResult.file_id == file_id)
        return self.db.execute(statement).scalar_one_or_none()

    def create(self, entity: DoclingParseResult) -> DoclingParseResult:
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def update(self, entity: DoclingParseResult) -> DoclingParseResult:
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity
