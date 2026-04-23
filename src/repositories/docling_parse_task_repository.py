from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from src.db.models.docling_parse_task import DoclingParseTask


class DoclingParseTaskRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_latest_by_file_id(self, file_id: str) -> DoclingParseTask | None:
        statement = (
            select(DoclingParseTask)
            .where(DoclingParseTask.file_id == file_id)
            .order_by(desc(DoclingParseTask.created_at), desc(DoclingParseTask.id))
        )
        return self.db.execute(statement).scalars().first()

    def get_by_task_id(self, task_id: str) -> DoclingParseTask | None:
        statement = select(DoclingParseTask).where(DoclingParseTask.task_id == task_id)
        return self.db.execute(statement).scalar_one_or_none()

    def list_recent(self, *, file_id: str | None = None, limit: int = 50) -> list[DoclingParseTask]:
        statement = select(DoclingParseTask)
        if file_id:
            statement = statement.where(DoclingParseTask.file_id == file_id)
        statement = statement.order_by(desc(DoclingParseTask.created_at), desc(DoclingParseTask.id)).limit(limit)
        return list(self.db.execute(statement).scalars().all())

    def create(self, entity: DoclingParseTask) -> DoclingParseTask:
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def update(self, entity: DoclingParseTask) -> DoclingParseTask:
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity
