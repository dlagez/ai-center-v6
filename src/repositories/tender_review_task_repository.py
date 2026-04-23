from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from src.db.models.tender_review_task import TenderReviewTask


class TenderReviewTaskRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, entity: TenderReviewTask) -> TenderReviewTask:
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def get_by_id(self, task_id: int) -> TenderReviewTask | None:
        statement = select(TenderReviewTask).where(TenderReviewTask.id == task_id)
        return self.db.execute(statement).scalar_one_or_none()

    def get_by_task_no(self, task_no: str) -> TenderReviewTask | None:
        statement = select(TenderReviewTask).where(TenderReviewTask.task_no == task_no)
        return self.db.execute(statement).scalar_one_or_none()

    def list(
        self,
        *,
        status: str | None = None,
        review_type: str | None = None,
        created_by: str | None = None,
        limit: int = 100,
    ) -> list[TenderReviewTask]:
        statement = select(TenderReviewTask)
        if status:
            statement = statement.where(TenderReviewTask.status == status)
        if review_type:
            statement = statement.where(TenderReviewTask.review_type == review_type)
        if created_by:
            statement = statement.where(TenderReviewTask.created_by == created_by)

        statement = statement.order_by(desc(TenderReviewTask.created_at), desc(TenderReviewTask.id)).limit(limit)
        return list(self.db.execute(statement).scalars().all())

    def update(self, entity: TenderReviewTask) -> TenderReviewTask:
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def delete(self, entity: TenderReviewTask) -> None:
        self.db.delete(entity)
        self.db.commit()
