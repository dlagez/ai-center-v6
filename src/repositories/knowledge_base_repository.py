from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from src.db.models.knowledge_base import KnowledgeBase


class KnowledgeBaseRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, entity: KnowledgeBase) -> KnowledgeBase:
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def update(self, entity: KnowledgeBase) -> KnowledgeBase:
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def delete(self, entity: KnowledgeBase) -> None:
        self.db.delete(entity)
        self.db.commit()

    def get_by_kb_id(self, kb_id: str) -> KnowledgeBase | None:
        statement = select(KnowledgeBase).where(KnowledgeBase.kb_id == kb_id)
        return self.db.execute(statement).scalar_one_or_none()

    def get_by_collection_name(self, collection_name: str) -> KnowledgeBase | None:
        statement = select(KnowledgeBase).where(KnowledgeBase.qdrant_collection == collection_name)
        return self.db.execute(statement).scalar_one_or_none()

    def list_all(self, *, status: str | None = None, limit: int = 200) -> list[KnowledgeBase]:
        statement = select(KnowledgeBase)
        if status:
            statement = statement.where(KnowledgeBase.status == status)
        statement = statement.order_by(desc(KnowledgeBase.updated_at), desc(KnowledgeBase.id)).limit(limit)
        return list(self.db.execute(statement).scalars().all())
