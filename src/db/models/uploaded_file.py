from datetime import datetime

from sqlalchemy import BIGINT, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id: Mapped[int] = mapped_column(BIGINT(), primary_key=True, autoincrement=True)
    file_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    file_name: Mapped[str] = mapped_column(String(255))
    stored_name: Mapped[str] = mapped_column(String(255))
    object_name: Mapped[str] = mapped_column(String(1024))
    bucket_name: Mapped[str] = mapped_column(String(128))
    biz_type: Mapped[str] = mapped_column(String(64), index=True)
    date_folder: Mapped[str] = mapped_column(String(32), index=True)
    folder_path: Mapped[str] = mapped_column(String(512), index=True)
    content_type: Mapped[str] = mapped_column(String(128), index=True)
    file_size: Mapped[int] = mapped_column(BIGINT())
    file_ext: Mapped[str | None] = mapped_column(String(32), nullable=True)
    biz_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    storage_provider: Mapped[str] = mapped_column(String(32), default="minio", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False, index=True)
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
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)
