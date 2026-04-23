from sqlalchemy import delete, desc, select
from sqlalchemy.orm import Session

from src.db.models.knowledge_document import KnowledgeDocument


class KnowledgeDocumentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, entity: KnowledgeDocument) -> KnowledgeDocument:
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def update(self, entity: KnowledgeDocument) -> KnowledgeDocument:
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def delete(self, entity: KnowledgeDocument) -> None:
        self.db.delete(entity)
        self.db.commit()

    def delete_by_kb_id(self, kb_id: str) -> None:
        self.db.execute(delete(KnowledgeDocument).where(KnowledgeDocument.kb_id == kb_id))
        self.db.commit()

    def get_by_kb_id_and_file_id(
        self,
        kb_id: str,
        file_id: str,
        *,
        chunker_type: str | None = None,
    ) -> KnowledgeDocument | None:
        statement = select(KnowledgeDocument).where(
            KnowledgeDocument.kb_id == kb_id,
            KnowledgeDocument.file_id == file_id,
        )
        if chunker_type:
            statement = statement.where(KnowledgeDocument.chunker_type == chunker_type)
        statement = statement.order_by(desc(KnowledgeDocument.updated_at), desc(KnowledgeDocument.id))
        return self.db.execute(statement).scalars().first()

    def list_by_kb_id(self, kb_id: str, *, limit: int = 500) -> list[KnowledgeDocument]:
        statement = (
            select(KnowledgeDocument)
            .where(KnowledgeDocument.kb_id == kb_id)
            .order_by(desc(KnowledgeDocument.updated_at), desc(KnowledgeDocument.id))
            .limit(limit)
        )
        return list(self.db.execute(statement).scalars().all())
