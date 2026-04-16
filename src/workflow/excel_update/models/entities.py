from datetime import datetime

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base

ID_TYPE = BigInteger().with_variant(Integer, "sqlite")


class ExcelTask(Base):
    __tablename__ = "excel_task"

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    task_name: Mapped[str] = mapped_column(String(255), nullable=False)
    original_file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    bucket_name: Mapped[str] = mapped_column(String(128), nullable=False)
    original_object_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    latest_version_id: Mapped[int | None] = mapped_column(ID_TYPE, nullable=True, index=True)
    current_version_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", server_default="active", index=True)
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class ExcelTaskVersion(Base):
    __tablename__ = "excel_task_version"
    __table_args__ = (
        UniqueConstraint("task_id", "version_no", name="uk_task_version_no"),
    )

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(ID_TYPE, ForeignKey("excel_task.id"), nullable=False, index=True)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    object_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(ID_TYPE, nullable=False, default=0, server_default="0")
    checksum_md5: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_operation_id: Mapped[int | None] = mapped_column(ID_TYPE, nullable=True, index=True)
    is_current: Mapped[bool] = mapped_column(Integer, nullable=False, default=0, server_default="0", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(), server_default=func.now(), nullable=False)


class ExcelOperation(Base):
    __tablename__ = "excel_operation"

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(ID_TYPE, ForeignKey("excel_task.id"), nullable=False, index=True)
    operation_no: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
        server_default="pending",
        index=True,
    )
    base_version_id: Mapped[int | None] = mapped_column(ID_TYPE, nullable=True, index=True)
    result_version_id: Mapped[int | None] = mapped_column(ID_TYPE, nullable=True, index=True)
    sheet_name: Mapped[str] = mapped_column(String(255), nullable=False)
    match_column: Mapped[str] = mapped_column(String(16), nullable=False)
    target_column: Mapped[str] = mapped_column(String(16), nullable=False)
    request_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    summary_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text(), nullable=True)
    total_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    success_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    not_found_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    duplicate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    submitted_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(), server_default=func.now(), nullable=False, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)


class ExcelOperationItemResult(Base):
    __tablename__ = "excel_operation_item_result"

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    operation_id: Mapped[int] = mapped_column(ID_TYPE, ForeignKey("excel_operation.id"), nullable=False, index=True)
    task_id: Mapped[int] = mapped_column(ID_TYPE, ForeignKey("excel_task.id"), nullable=False, index=True)
    match_value: Mapped[str] = mapped_column(String(1024), nullable=False)
    target_value: Mapped[str | None] = mapped_column(Text(), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    row_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cell_address: Mapped[str | None] = mapped_column(String(32), nullable=True)
    old_value: Mapped[str | None] = mapped_column(Text(), nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text(), nullable=True)
    message: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(), server_default=func.now(), nullable=False)
