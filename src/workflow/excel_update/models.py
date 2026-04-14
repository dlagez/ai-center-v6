from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base


class ExcelUpdateTask(Base):
    __tablename__ = "excel_update_tasks"

    task_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    file_name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False)
    operation_count: Mapped[int] = mapped_column(Integer(), default=0, nullable=False)
    latest_target_column: Mapped[str | None] = mapped_column(String(255), nullable=True)
    latest_output_file_name: Mapped[str] = mapped_column(String(255))
    detail_url: Mapped[str] = mapped_column(String(255))
    download_url: Mapped[str] = mapped_column(String(255))
    source_excel_path: Mapped[str] = mapped_column(Text())
    current_excel_path: Mapped[str] = mapped_column(Text())
    created_record_at: Mapped[datetime] = mapped_column(
        DateTime(),
        server_default=func.now(),
        nullable=False,
    )
    updated_record_at: Mapped[datetime] = mapped_column(
        DateTime(),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    operations: Mapped[list["ExcelUpdateOperation"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="ExcelUpdateOperation.sequence",
    )


class ExcelUpdateOperation(Base):
    __tablename__ = "excel_update_operations"

    operation_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("excel_update_tasks.task_id", ondelete="CASCADE"),
        index=True,
    )
    sequence: Mapped[int] = mapped_column(Integer(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False)
    output_file_name: Mapped[str] = mapped_column(String(255))
    download_url: Mapped[str] = mapped_column(String(255))
    detail_url: Mapped[str] = mapped_column(String(255))
    request_payload: Mapped[dict] = mapped_column(JSON())
    analysis_payload: Mapped[dict | None] = mapped_column(JSON(), nullable=True)
    result_payload: Mapped[dict] = mapped_column(JSON())
    created_record_at: Mapped[datetime] = mapped_column(
        DateTime(),
        server_default=func.now(),
        nullable=False,
    )

    task: Mapped[ExcelUpdateTask] = relationship(back_populates="operations")
