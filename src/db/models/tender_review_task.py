from datetime import datetime

from sqlalchemy import BIGINT, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class TenderReviewTask(Base):
    __tablename__ = "tender_review_task"

    id: Mapped[int] = mapped_column(BIGINT(), primary_key=True, autoincrement=True)
    task_no: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    project_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    document_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    document_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    document_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    review_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="init", index=True)
    catalog_count: Mapped[int] = mapped_column(nullable=False, default=0)
    completed_count: Mapped[int] = mapped_column(nullable=False, default=0)
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
