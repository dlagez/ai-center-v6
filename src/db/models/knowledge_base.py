from datetime import datetime

from sqlalchemy import BIGINT, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class KnowledgeBase(Base):
    __tablename__ = "knowledge_base"

    id: Mapped[int] = mapped_column(BIGINT(), primary_key=True, autoincrement=True)
    kb_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    biz_type: Mapped[str] = mapped_column(String(64), nullable=False, default="general", index=True)
    embedding_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    chunker_type: Mapped[str] = mapped_column(String(32), nullable=False, default="default")
    qdrant_collection: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True)
    document_count: Mapped[int] = mapped_column(nullable=False, default=0)
    chunk_count: Mapped[int] = mapped_column(nullable=False, default=0)
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
