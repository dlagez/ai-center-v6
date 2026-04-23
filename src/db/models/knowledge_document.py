from datetime import datetime

from sqlalchemy import BIGINT, DateTime, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_document"
    __table_args__ = (
        UniqueConstraint("kb_id", "file_id", "chunker_type", name="uk_knowledge_document_kb_file_chunker"),
    )

    id: Mapped[int] = mapped_column(BIGINT(), primary_key=True, autoincrement=True)
    kb_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    file_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    parse_task_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    chunker_type: Mapped[str] = mapped_column(String(32), nullable=False, default="default")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    chunk_count: Mapped[int] = mapped_column(nullable=False, default=0)
    page_count: Mapped[int] = mapped_column(nullable=False, default=0)
    sample_heading: Mapped[str | None] = mapped_column(String(255), nullable=True)
    folder_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    retry_count: Mapped[int] = mapped_column(nullable=False, default=0)
    current_stage: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    last_error_stage: Mapped[str | None] = mapped_column(String(32), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text(), nullable=True)
    last_index_started_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)
    last_index_finished_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)
    last_retry_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)
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
