from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models.docling_parse_result import DoclingParseResult


class DoclingParseResultRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_by_task_id(self, task_id: str) -> list[DoclingParseResult]:
        statement = (
            select(DoclingParseResult)
            .where(DoclingParseResult.task_id == task_id)
            .order_by(DoclingParseResult.page_no.asc(), DoclingParseResult.id.asc())
        )
        return list(self.db.execute(statement).scalars().all())

    def get_by_task_id_and_page_no(self, task_id: str, page_no: int) -> DoclingParseResult | None:
        statement = select(DoclingParseResult).where(
            DoclingParseResult.task_id == task_id,
            DoclingParseResult.page_no == page_no,
        )
        return self.db.execute(statement).scalar_one_or_none()

    def create(self, entity: DoclingParseResult) -> DoclingParseResult:
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def create_many(self, entities: list[DoclingParseResult]) -> list[DoclingParseResult]:
        self.db.add_all(entities)
        self.db.commit()
        for entity in entities:
            self.db.refresh(entity)
        return entities

    def update(self, entity: DoclingParseResult) -> DoclingParseResult:
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity
