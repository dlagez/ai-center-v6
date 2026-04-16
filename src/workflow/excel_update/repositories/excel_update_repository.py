from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import Select, func, select, update
from sqlalchemy.orm import Session

from src.workflow.excel_update.models import (
    ExcelOperation,
    ExcelOperationItemResult,
    ExcelTask,
    ExcelTaskVersion,
)


class ExcelUpdateRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_task(
        self,
        *,
        task_name: str,
        original_file_name: str,
        bucket_name: str,
        original_object_key: str,
        created_by: str | None,
    ) -> ExcelTask:
        item = ExcelTask(
            task_name=task_name,
            original_file_name=original_file_name,
            bucket_name=bucket_name,
            original_object_key=original_object_key,
            created_by=created_by,
        )
        self.db.add(item)
        self.db.flush()
        return item

    def create_version(
        self,
        *,
        task_id: int,
        version_no: int,
        object_key: str,
        file_name: str,
        file_size: int,
        checksum_md5: str | None,
        source_operation_id: int | None,
        is_current: bool,
    ) -> ExcelTaskVersion:
        item = ExcelTaskVersion(
            task_id=task_id,
            version_no=version_no,
            object_key=object_key,
            file_name=file_name,
            file_size=file_size,
            checksum_md5=checksum_md5,
            source_operation_id=source_operation_id,
            is_current=1 if is_current else 0,
        )
        self.db.add(item)
        self.db.flush()
        return item

    def create_operation(
        self,
        *,
        task_id: int,
        operation_no: str,
        sheet_name: str,
        match_column: str,
        target_column: str,
        request_payload: dict,
        total_count: int,
        submitted_by: str | None,
    ) -> ExcelOperation:
        item = ExcelOperation(
            task_id=task_id,
            operation_no=operation_no,
            sheet_name=sheet_name,
            match_column=match_column,
            target_column=target_column,
            request_payload=request_payload,
            total_count=total_count,
            submitted_by=submitted_by,
        )
        self.db.add(item)
        self.db.flush()
        return item

    def add_operation_item_results(
        self,
        *,
        operation_id: int,
        task_id: int,
        items: Sequence[dict],
    ) -> list[ExcelOperationItemResult]:
        rows = [
            ExcelOperationItemResult(
                operation_id=operation_id,
                task_id=task_id,
                **item,
            )
            for item in items
        ]
        self.db.add_all(rows)
        self.db.flush()
        return rows

    def get_task(self, task_id: int) -> ExcelTask | None:
        return self.db.get(ExcelTask, task_id)

    def get_task_with_lock(self, task_id: int) -> ExcelTask | None:
        stmt = select(ExcelTask).where(ExcelTask.id == task_id)
        if _supports_for_update(self.db):
            stmt = stmt.with_for_update()
        return self.db.scalar(stmt)

    def get_version(self, version_id: int) -> ExcelTaskVersion | None:
        return self.db.get(ExcelTaskVersion, version_id)

    def get_operation(self, operation_id: int) -> ExcelOperation | None:
        return self.db.get(ExcelOperation, operation_id)

    def get_operation_with_lock(self, operation_id: int) -> ExcelOperation | None:
        stmt = select(ExcelOperation).where(ExcelOperation.id == operation_id)
        if _supports_for_update(self.db):
            stmt = stmt.with_for_update()
        return self.db.scalar(stmt)

    def get_current_version(self, task_id: int) -> ExcelTaskVersion | None:
        stmt = (
            select(ExcelTaskVersion)
            .where(ExcelTaskVersion.task_id == task_id)
            .order_by(ExcelTaskVersion.version_no.desc())
            .limit(1)
        )
        return self.db.scalar(stmt)

    def get_operation_for_task(self, task_id: int, operation_id: int) -> ExcelOperation | None:
        stmt = select(ExcelOperation).where(
            ExcelOperation.id == operation_id,
            ExcelOperation.task_id == task_id,
        )
        return self.db.scalar(stmt)

    def get_version_for_task(self, task_id: int, version_id: int) -> ExcelTaskVersion | None:
        stmt = select(ExcelTaskVersion).where(
            ExcelTaskVersion.id == version_id,
            ExcelTaskVersion.task_id == task_id,
        )
        return self.db.scalar(stmt)

    def list_tasks(self, *, page: int, page_size: int) -> list[ExcelTask]:
        stmt = (
            select(ExcelTask)
            .order_by(ExcelTask.updated_at.desc(), ExcelTask.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(self.db.scalars(stmt))

    def count_tasks(self) -> int:
        stmt = select(func.count()).select_from(ExcelTask)
        return int(self.db.scalar(stmt) or 0)

    def list_operations(
        self,
        *,
        task_id: int,
        page: int,
        page_size: int,
        status: str | None = None,
    ) -> list[ExcelOperation]:
        stmt = (
            select(ExcelOperation)
            .where(ExcelOperation.task_id == task_id)
            .order_by(ExcelOperation.submitted_at.desc(), ExcelOperation.id.desc())
        )
        if status:
            stmt = stmt.where(ExcelOperation.status == status)
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        return list(self.db.scalars(stmt))

    def count_operations(self, *, task_id: int, status: str | None = None) -> int:
        stmt = select(func.count()).select_from(ExcelOperation).where(ExcelOperation.task_id == task_id)
        if status:
            stmt = stmt.where(ExcelOperation.status == status)
        return int(self.db.scalar(stmt) or 0)

    def list_versions(self, *, task_id: int, page: int, page_size: int) -> list[ExcelTaskVersion]:
        stmt = (
            select(ExcelTaskVersion)
            .where(ExcelTaskVersion.task_id == task_id)
            .order_by(ExcelTaskVersion.version_no.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(self.db.scalars(stmt))

    def count_versions(self, *, task_id: int) -> int:
        stmt = select(func.count()).select_from(ExcelTaskVersion).where(ExcelTaskVersion.task_id == task_id)
        return int(self.db.scalar(stmt) or 0)

    def list_operation_items(
        self,
        *,
        operation_id: int,
        page: int,
        page_size: int,
    ) -> list[ExcelOperationItemResult]:
        stmt = (
            select(ExcelOperationItemResult)
            .where(ExcelOperationItemResult.operation_id == operation_id)
            .order_by(ExcelOperationItemResult.id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(self.db.scalars(stmt))

    def count_operation_items(self, *, operation_id: int) -> int:
        stmt = select(func.count()).select_from(ExcelOperationItemResult).where(
            ExcelOperationItemResult.operation_id == operation_id
        )
        return int(self.db.scalar(stmt) or 0)

    def get_task_stats(self, task_id: int) -> tuple[int, datetime | None]:
        stmt = select(
            func.count(ExcelOperation.id),
            func.max(ExcelOperation.submitted_at),
        ).where(ExcelOperation.task_id == task_id)
        count_value, last_operation_time = self.db.execute(stmt).one()
        return int(count_value or 0), last_operation_time

    def count_running_operations(self, task_id: int, exclude_operation_id: int | None = None) -> int:
        stmt = select(func.count()).select_from(ExcelOperation).where(
            ExcelOperation.task_id == task_id,
            ExcelOperation.status == "running",
        )
        if exclude_operation_id is not None:
            stmt = stmt.where(ExcelOperation.id != exclude_operation_id)
        return int(self.db.scalar(stmt) or 0)

    def list_pending_operations_for_claim(self, limit: int = 20) -> list[ExcelOperation]:
        stmt: Select[tuple[ExcelOperation]] = (
            select(ExcelOperation)
            .where(ExcelOperation.status == "pending")
            .order_by(ExcelOperation.submitted_at.asc(), ExcelOperation.id.asc())
            .limit(limit)
        )
        if _supports_for_update(self.db):
            stmt = stmt.with_for_update(skip_locked=True)
        return list(self.db.scalars(stmt))

    def mark_all_versions_not_current(self, task_id: int) -> None:
        self.db.execute(
            update(ExcelTaskVersion)
            .where(ExcelTaskVersion.task_id == task_id, ExcelTaskVersion.is_current == 1)
            .values(is_current=0)
        )


def _supports_for_update(db: Session) -> bool:
    bind = db.get_bind()
    return bind is not None and bind.dialect.name != "sqlite"
