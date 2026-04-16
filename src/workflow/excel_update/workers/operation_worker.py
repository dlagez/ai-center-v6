from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.session import SessionLocal, get_engine
from src.workflow.excel_update.models import ExcelOperation
from src.workflow.excel_update.excel import OpenpyxlExcelEngine
from src.workflow.excel_update.repositories import ExcelUpdateRepository
from src.workflow.excel_update.schemas import OperationExecutionResult
from src.workflow.excel_update.services.storage import ExcelStorageService
from src.workflow.excel_update.utils import now_local


class OperationWorker:
    def __init__(self):
        get_engine()
        self.storage = ExcelStorageService()
        self.engine = OpenpyxlExcelEngine()

    def process_pending_operations(self) -> None:
        self.fail_stale_running_operations()
        while True:
            operation_id = self._claim_next_operation()
            if operation_id is None:
                return
            self._execute_operation(operation_id)

    def fail_stale_running_operations(self) -> None:
        cutoff = _naive_now() - timedelta(hours=1)
        with SessionLocal() as db, db.begin():
            stale_operations = list(
                db.scalars(
                    select(ExcelOperation).where(
                        ExcelOperation.status == "running",
                        ExcelOperation.started_at.is_not(None),
                        ExcelOperation.started_at < cutoff,
                    )
                )
            )
            for operation in stale_operations:
                operation.status = "failed"
                operation.error_message = "operation timeout"
                operation.finished_at = _naive_now()
                if not operation.summary_payload:
                    operation.summary_payload = {
                        "total_count": operation.total_count,
                        "success_count": operation.success_count,
                        "not_found_count": operation.not_found_count,
                        "duplicate_count": operation.duplicate_count,
                        "failed_count": max(operation.failed_count, operation.total_count - operation.success_count),
                    }
                operation.failed_count = max(
                    operation.failed_count,
                    operation.total_count - operation.success_count,
                )

    def _claim_next_operation(self) -> int | None:
        with SessionLocal() as db:
            with db.begin():
                repo = ExcelUpdateRepository(db)
                pending_ops = repo.list_pending_operations_for_claim()
                for operation in pending_ops:
                    locked_task = repo.get_task_with_lock(operation.task_id)
                    if locked_task is None:
                        continue
                    running_count = repo.count_running_operations(
                        operation.task_id,
                        exclude_operation_id=operation.id,
                    )
                    if running_count:
                        continue
                    locked_operation = repo.get_operation_with_lock(operation.id)
                    if locked_operation is None or locked_operation.status != "pending":
                        continue
                    locked_operation.status = "running"
                    locked_operation.started_at = _naive_now()
                    locked_operation.base_version_id = locked_task.latest_version_id
                    db.flush()
                    return locked_operation.id
            return None

    def _execute_operation(self, operation_id: int) -> None:
        with SessionLocal() as db:
            repo = ExcelUpdateRepository(db)
            operation = repo.get_operation(operation_id)
            if operation is None:
                return
            task = repo.get_task(operation.task_id)
            if task is None:
                operation.status = "failed"
                operation.error_message = "task not found"
                operation.finished_at = _naive_now()
                db.commit()
                return
            base_version = repo.get_version(operation.base_version_id or task.latest_version_id)
            if base_version is None:
                operation.status = "failed"
                operation.error_message = "base version not found"
                operation.finished_at = _naive_now()
                db.commit()
                return

            try:
                base_payload = self.storage.download_bytes(base_version.object_key)
                request_payload = operation.request_payload
                with TemporaryDirectory(prefix="excel-update-") as temp_dir:
                    temp_path = Path(temp_dir)
                    input_path = temp_path / "base.xlsx"
                    output_path = temp_path / "updated.xlsx"
                    input_path.write_bytes(base_payload)
                    execution_result = self.engine.apply_updates(
                        input_path=input_path,
                        output_path=output_path,
                        sheet_name=operation.sheet_name,
                        match_column=operation.match_column,
                        target_column=operation.target_column,
                        updates=request_payload["updates"],
                    )
                    self._persist_result(
                        db=db,
                        repo=repo,
                        task=task,
                        operation=operation,
                        base_version=base_version,
                        execution_result=execution_result,
                        output_path=output_path,
                    )
            except Exception as exc:
                operation.status = "failed"
                operation.error_message = str(exc)
                operation.finished_at = _naive_now()
                operation.summary_payload = {
                    "total_count": operation.total_count,
                    "success_count": 0,
                    "not_found_count": 0,
                    "duplicate_count": 0,
                    "failed_count": operation.total_count,
                }
                operation.failed_count = operation.total_count
                db.commit()

    def _persist_result(
        self,
        *,
        db: Session,
        repo: ExcelUpdateRepository,
        task,
        operation,
        base_version,
        execution_result: OperationExecutionResult,
        output_path: Path,
    ) -> None:
        item_rows = [
            {
                "match_value": item.match_value,
                "target_value": None if item.target_value is None else str(item.target_value),
                "status": item.status,
                "row_index": item.row_index,
                "cell_address": item.cell_address,
                "old_value": item.old_value,
                "new_value": item.new_value,
                "message": item.message,
            }
            for item in execution_result.items
        ]
        repo.add_operation_item_results(
            operation_id=operation.id,
            task_id=task.id,
            items=item_rows,
        )

        summary = execution_result.summary.model_dump()
        operation.summary_payload = summary
        operation.success_count = execution_result.summary.success_count
        operation.not_found_count = execution_result.summary.not_found_count
        operation.duplicate_count = execution_result.summary.duplicate_count
        operation.failed_count = execution_result.summary.failed_count

        if execution_result.has_successful_updates:
            payload = output_path.read_bytes()
            next_version_no = task.current_version_no + 1
            object_key = f"excel-task/{task.id}/versions/v{next_version_no:04d}.xlsx"
            stored_object = self.storage.save_bytes(payload=payload, object_key=object_key)
            repo.mark_all_versions_not_current(task.id)
            new_version = repo.create_version(
                task_id=task.id,
                version_no=next_version_no,
                object_key=stored_object.object_key,
                file_name=f"v{next_version_no:04d}.xlsx",
                file_size=stored_object.file_size,
                checksum_md5=stored_object.checksum_md5,
                source_operation_id=operation.id,
                is_current=True,
            )
            task.latest_version_id = new_version.id
            task.current_version_no = next_version_no
            operation.result_version_id = new_version.id

        operation.status = self._resolve_final_status(execution_result)
        operation.finished_at = _naive_now()
        db.commit()

    @staticmethod
    def _resolve_final_status(execution_result: OperationExecutionResult) -> str:
        summary = execution_result.summary
        if summary.success_count == summary.total_count:
            return "success"
        if summary.success_count > 0:
            return "partial_success"
        if summary.failed_count == summary.total_count:
            return "failed"
        return "partial_success"


def _naive_now():
    return now_local().replace(tzinfo=None)
