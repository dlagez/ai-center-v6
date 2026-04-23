from sqlalchemy import asc, select
from sqlalchemy.orm import Session

from src.db.models.tender_review_item import TenderReviewItem


class TenderReviewItemRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, entity: TenderReviewItem) -> TenderReviewItem:
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def create_many(self, entities: list[TenderReviewItem]) -> list[TenderReviewItem]:
        self.db.add_all(entities)
        self.db.commit()
        for entity in entities:
            self.db.refresh(entity)
        return entities

    def get_by_id(self, item_id: int) -> TenderReviewItem | None:
        statement = select(TenderReviewItem).where(TenderReviewItem.id == item_id)
        return self.db.execute(statement).scalar_one_or_none()

    def list_by_task_id(
        self,
        task_id: int,
        *,
        parent_id: int | None = None,
        generation_status: str | None = None,
        manual_status: str | None = None,
    ) -> list[TenderReviewItem]:
        statement = select(TenderReviewItem).where(TenderReviewItem.task_id == task_id)
        if parent_id is None:
            statement = statement.where(TenderReviewItem.parent_id.is_(None))
        elif parent_id >= 0:
            statement = statement.where(TenderReviewItem.parent_id == parent_id)
        if generation_status:
            statement = statement.where(TenderReviewItem.generation_status == generation_status)
        if manual_status:
            statement = statement.where(TenderReviewItem.manual_status == manual_status)

        statement = statement.order_by(
            asc(TenderReviewItem.seq_no),
            asc(TenderReviewItem.id),
        )
        return list(self.db.execute(statement).scalars().all())

    def list_all_by_task_id(self, task_id: int) -> list[TenderReviewItem]:
        statement = (
            select(TenderReviewItem)
            .where(TenderReviewItem.task_id == task_id)
            .order_by(asc(TenderReviewItem.level), asc(TenderReviewItem.seq_no), asc(TenderReviewItem.id))
        )
        return list(self.db.execute(statement).scalars().all())

    def update(self, entity: TenderReviewItem) -> TenderReviewItem:
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def delete(self, entity: TenderReviewItem) -> None:
        self.db.delete(entity)
        self.db.commit()

    def delete_by_task_id(self, task_id: int) -> None:
        entities = self.list_all_by_task_id(task_id)
        for entity in entities:
            self.db.delete(entity)
        self.db.commit()
