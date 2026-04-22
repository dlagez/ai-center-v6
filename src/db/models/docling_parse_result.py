from datetime import datetime

from sqlalchemy import BIGINT, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class DoclingParseResult(Base):
    __tablename__ = "docling_parse_results"

    id: Mapped[int] = mapped_column(BIGINT(), primary_key=True, autoincrement=True)
    result_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    task_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    file_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    batch_no: Mapped[int] = mapped_column(nullable=False, default=0, index=True)
    page_no: Mapped[int] = mapped_column(nullable=False, index=True)
    parser_name: Mapped[str] = mapped_column(String(64), default="docling", nullable=False)
    parser_version: Mapped[str] = mapped_column(String(64), nullable=False)
    parse_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, index=True)
    error_message: Mapped[str | None] = mapped_column(Text(), nullable=True)
    result_json: Mapped[str | None] = mapped_column(Text().with_variant(Text(length=4294967295), "mysql"), nullable=True)
    markdown: Mapped[str | None] = mapped_column(Text().with_variant(Text(length=4294967295), "mysql"), nullable=True)
    block_count: Mapped[int] = mapped_column(nullable=False, default=0)
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
