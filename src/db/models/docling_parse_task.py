from datetime import datetime

from sqlalchemy import BIGINT, DateTime, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class DoclingParseTask(Base):
    __tablename__ = "docling_parse_tasks"

    id: Mapped[int] = mapped_column(BIGINT(), primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    file_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    parser_name: Mapped[str] = mapped_column(String(64), default="docling", nullable=False)
    parser_version: Mapped[str] = mapped_column(String(64), nullable=False)
    parse_config_json: Mapped[str | None] = mapped_column(Text(), nullable=True)
    batch_size: Mapped[int] = mapped_column(nullable=False, default=10)
    current_batch_no: Mapped[int] = mapped_column(nullable=False, default=0)
    total_pages: Mapped[int] = mapped_column(nullable=False, default=0)
    parsed_pages: Mapped[int] = mapped_column(nullable=False, default=0)
    failed_pages: Mapped[int] = mapped_column(nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, index=True)
    progress: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0.00)
    error_message: Mapped[str | None] = mapped_column(Text(), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)
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
