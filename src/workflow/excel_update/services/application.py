from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from src.db.session import SessionLocal, get_engine
from src.workflow.excel_update.excel import OpenpyxlExcelEngine
from src.workflow.excel_update.repositories import ExcelUpdateRepository
from src.workflow.excel_update.schemas import (
    CreateOperationRequest,
    DownloadUrlData,
    DownloadedFile,
    OperationDetailData,
    OperationItemResultData,
    OperationListData,
    OperationStatusData,
    OperationSummaryData,
    TaskDetailData,
    TaskListData,
    UploadTaskData,
    VersionInfoData,
    VersionListData,
)
from src.workflow.excel_update.services.errors import ExcelUpdateError
from src.workflow.excel_update.services.storage import ExcelStorageService
from src.workflow.excel_update.utils import decode_download_token, encode_download_token, normalize_excel_column, to_iso8601


class ExcelUpdateAppService:
    def __init__(self):
        get_engine()
        self.storage = ExcelStorageService()
        self.engine = OpenpyxlExcelEngine()

    def upload_task(
        self,
        *,
        file_name: str,
        payload: bytes,
        task_name: str | None = None,
        created_by: str | None = None,
    ) -> UploadTaskData:
        self._validate_xlsx_file(file_name=file_name, payload=payload)
        resolved_task_name = (task_name or Path(file_name).stem).strip() or Path(file_name).stem or "excel-task"

        object_key = ""
        with self._session_scope() as db:
            repo = ExcelUpdateRepository(db)
            task = repo.create_task(
                task_name=resolved_task_name,
                original_file_name=file_name,
                bucket_name=self.storage.bucket_name,
                original_object_key="pending",
                created_by=created_by,
            )
            object_key = f"excel-task/{task.id}/original/{Path(file_name).name}"
            try:
                stored_object = self.storage.save_bytes(payload=payload, object_key=object_key)
            except Exception as exc:
                raise ExcelUpdateError(code=50000, http_status=500, message="failed to upload excel file") from exc
            task.bucket_name = stored_object.bucket_name
            task.original_object_key = stored_object.object_key
            version = repo.create_version(
                task_id=task.id,
                version_no=1,
                object_key=stored_object.object_key,
                file_name=file_name,
                file_size=stored_object.file_size,
                checksum_md5=stored_object.checksum_md5,
                source_operation_id=None,
                is_current=True,
            )
            task.latest_version_id = version.id
            task.current_version_no = 1
            db.flush()
            return UploadTaskData(
                task_id=task.id,
                task_name=task.task_name,
                original_file_name=task.original_file_name,
                current_version_no=task.current_version_no,
                latest_version_id=version.id,
                status=task.status,
                created_at=to_iso8601(task.created_at),
            )

    def list_tasks(self, *, page: int, page_size: int) -> TaskListData:
        with self._session_scope() as db:
            repo = ExcelUpdateRepository(db)
            items = []
            for task in repo.list_tasks(page=page, page_size=page_size):
                operation_count, last_operation_time = repo.get_task_stats(task.id)
                items.append(
                    {
                        "task_id": task.id,
                        "task_name": task.task_name,
                        "original_file_name": task.original_file_name,
                        "current_version_no": task.current_version_no,
                        "operation_count": operation_count,
                        "last_operation_time": to_iso8601(last_operation_time),
                        "created_at": to_iso8601(task.created_at),
                        "updated_at": to_iso8601(task.updated_at),
                    }
                )
            return TaskListData(
                page=page,
                page_size=page_size,
                total=repo.count_tasks(),
                items=items,
            )

    def get_task_detail(self, task_id: int) -> TaskDetailData:
        with self._session_scope() as db:
            repo = ExcelUpdateRepository(db)
            task = repo.get_task(task_id)
            if task is None:
                raise ExcelUpdateError(code=40004, http_status=404, message="task not found")
            latest_version = repo.get_version(task.latest_version_id)
            if latest_version is None:
                raise ExcelUpdateError(code=40004, http_status=404, message="latest version not found")
            sheet_names = self.engine.list_sheet_names(self.storage.download_bytes(latest_version.object_key))
            operation_count, last_operation_time = repo.get_task_stats(task.id)
            return TaskDetailData(
                task_id=task.id,
                task_name=task.task_name,
                original_file_name=task.original_file_name,
                status=task.status,
                created_by=task.created_by,
                created_at=to_iso8601(task.created_at),
                updated_at=to_iso8601(task.updated_at),
                current_version_no=task.current_version_no,
                latest_version=self._build_version_info(latest_version, include_download=False),
                stats={
                    "operation_count": operation_count,
                    "last_operation_time": to_iso8601(last_operation_time),
                },
                sheet_names=sheet_names,
            )

    def create_operation(self, task_id: int, request: CreateOperationRequest) -> dict:
        with self._session_scope() as db:
            repo = ExcelUpdateRepository(db)
            task = repo.get_task(task_id)
            if task is None:
                raise ExcelUpdateError(code=40004, http_status=404, message="task not found")
            latest_version = repo.get_version(task.latest_version_id)
            if latest_version is None:
                raise ExcelUpdateError(code=40004, http_status=404, message="latest version not found")

            sheet_names = self.engine.list_sheet_names(self.storage.download_bytes(latest_version.object_key))
            if request.sheet_name not in sheet_names:
                raise ExcelUpdateError(
                    code=40001,
                    http_status=400,
                    message="invalid request",
                    error={"field": "sheet_name", "reason": "sheet not found"},
                )

            try:
                match_column = normalize_excel_column(request.match_column)
                target_column = normalize_excel_column(request.target_column)
            except ValueError as exc:
                raise ExcelUpdateError(
                    code=40001,
                    http_status=400,
                    message="invalid request",
                    error={"field": "match_column/target_column", "reason": str(exc)},
                ) from exc

            operation = repo.create_operation(
                task_id=task.id,
                operation_no=self._build_operation_no(),
                sheet_name=request.sheet_name,
                match_column=match_column,
                target_column=target_column,
                request_payload=request.model_dump(mode="json"),
                total_count=len(request.updates),
                submitted_by=request.submitted_by,
            )
            return {
                "operation_id": operation.id,
                "operation_no": operation.operation_no,
                "task_id": task.id,
                "status": operation.status,
                "submitted_at": to_iso8601(operation.submitted_at),
            }

    def list_operations(
        self,
        *,
        task_id: int,
        page: int,
        page_size: int,
        status: str | None,
    ) -> OperationListData:
        with self._session_scope() as db:
            repo = ExcelUpdateRepository(db)
            self._ensure_task_exists(repo, task_id)
            items = [
                {
                    "operation_id": item.id,
                    "operation_no": item.operation_no,
                    "status": item.status,
                    "sheet_name": item.sheet_name,
                    "match_column": item.match_column,
                    "target_column": item.target_column,
                    "total_count": item.total_count,
                    "success_count": item.success_count,
                    "not_found_count": item.not_found_count,
                    "duplicate_count": item.duplicate_count,
                    "failed_count": item.failed_count,
                    "submitted_by": item.submitted_by,
                    "submitted_at": to_iso8601(item.submitted_at),
                    "finished_at": to_iso8601(item.finished_at),
                    "result_version_id": item.result_version_id,
                }
                for item in repo.list_operations(task_id=task_id, page=page, page_size=page_size, status=status)
            ]
            return OperationListData(
                page=page,
                page_size=page_size,
                total=repo.count_operations(task_id=task_id, status=status),
                items=items,
            )

    def get_operation_detail(
        self,
        *,
        task_id: int,
        operation_id: int,
        include_items: bool,
        page: int,
        page_size: int,
        base_url: str,
    ) -> OperationDetailData:
        with self._session_scope() as db:
            repo = ExcelUpdateRepository(db)
            operation = repo.get_operation_for_task(task_id, operation_id)
            if operation is None:
                raise ExcelUpdateError(code=40004, http_status=404, message="operation not found")

            result_version = (
                self._build_version_info(repo.get_version(operation.result_version_id), include_download=True, base_url=base_url)
                if operation.result_version_id
                else None
            )
            item_total = repo.count_operation_items(operation_id=operation.id) if include_items else 0
            item_rows = repo.list_operation_items(operation_id=operation.id, page=page, page_size=page_size) if include_items else []
            items = [
                OperationItemResultData(
                    id=item.id,
                    match_value=item.match_value,
                    target_value=item.target_value,
                    status=item.status,
                    row_index=item.row_index,
                    cell_address=item.cell_address,
                    old_value=item.old_value,
                    new_value=item.new_value,
                    message=item.message,
                )
                for item in item_rows
            ]
            summary = OperationSummaryData(
                total_count=operation.total_count,
                success_count=operation.success_count,
                not_found_count=operation.not_found_count,
                duplicate_count=operation.duplicate_count,
                failed_count=operation.failed_count,
            )
            return OperationDetailData(
                operation_id=operation.id,
                operation_no=operation.operation_no,
                task_id=operation.task_id,
                status=operation.status,
                base_version_id=operation.base_version_id,
                result_version_id=operation.result_version_id,
                sheet_name=operation.sheet_name,
                match_column=operation.match_column,
                target_column=operation.target_column,
                request_payload=operation.request_payload,
                summary=summary,
                error_message=operation.error_message,
                submitted_by=operation.submitted_by,
                submitted_at=to_iso8601(operation.submitted_at),
                started_at=to_iso8601(operation.started_at),
                finished_at=to_iso8601(operation.finished_at),
                result_version=result_version,
                item_page=page,
                item_page_size=page_size,
                item_total=item_total,
                items=items,
            )

    def get_operation_status(self, *, task_id: int, operation_id: int) -> OperationStatusData:
        with self._session_scope() as db:
            repo = ExcelUpdateRepository(db)
            operation = repo.get_operation_for_task(task_id, operation_id)
            if operation is None:
                raise ExcelUpdateError(code=40004, http_status=404, message="operation not found")
            return OperationStatusData(
                operation_id=operation.id,
                status=operation.status,
                submitted_at=to_iso8601(operation.submitted_at),
                started_at=to_iso8601(operation.started_at),
                finished_at=to_iso8601(operation.finished_at),
                summary=OperationSummaryData(
                    total_count=operation.total_count,
                    success_count=operation.success_count,
                    not_found_count=operation.not_found_count,
                    duplicate_count=operation.duplicate_count,
                    failed_count=operation.failed_count,
                ),
            )

    def list_versions(self, *, task_id: int, page: int, page_size: int, base_url: str) -> VersionListData:
        with self._session_scope() as db:
            repo = ExcelUpdateRepository(db)
            self._ensure_task_exists(repo, task_id)
            items = [
                self._build_version_info(item, include_download=False, base_url=base_url)
                for item in repo.list_versions(task_id=task_id, page=page, page_size=page_size)
            ]
            return VersionListData(
                page=page,
                page_size=page_size,
                total=repo.count_versions(task_id=task_id),
                items=items,
            )

    def get_latest_download(self, *, task_id: int, base_url: str) -> DownloadUrlData:
        with self._session_scope() as db:
            repo = ExcelUpdateRepository(db)
            task = repo.get_task(task_id)
            if task is None:
                raise ExcelUpdateError(code=40004, http_status=404, message="task not found")
            version = repo.get_version(task.latest_version_id)
            if version is None:
                raise ExcelUpdateError(code=40004, http_status=404, message="latest version not found")
            return self._build_download_data(task_id=task_id, version=version, base_url=base_url)

    def get_version_download(self, *, task_id: int, version_id: int, base_url: str) -> DownloadUrlData:
        with self._session_scope() as db:
            repo = ExcelUpdateRepository(db)
            version = repo.get_version_for_task(task_id, version_id)
            if version is None:
                raise ExcelUpdateError(code=40004, http_status=404, message="version not found")
            return self._build_download_data(task_id=task_id, version=version, base_url=base_url)

    def get_original_download(self, *, task_id: int, base_url: str) -> DownloadUrlData:
        with self._session_scope() as db:
            repo = ExcelUpdateRepository(db)
            task = repo.get_task(task_id)
            if task is None:
                raise ExcelUpdateError(code=40004, http_status=404, message="task not found")
            return DownloadUrlData(
                task_id=task.id,
                file_name=task.original_file_name,
                download_url=self._build_download_url(
                    base_url=base_url,
                    object_key=task.original_object_key,
                    file_name=task.original_file_name,
                ),
            )

    def get_downloaded_file(self, download_token: str) -> DownloadedFile:
        try:
            payload = decode_download_token(download_token)
        except ValueError as exc:
            raise ExcelUpdateError(code=40001, http_status=400, message="invalid request") from exc
        return DownloadedFile(
            file_name=payload["file_name"],
            content=self.storage.download_bytes(payload["object_key"]),
        )

    @staticmethod
    def _validate_xlsx_file(*, file_name: str, payload: bytes) -> None:
        if not file_name or not file_name.lower().endswith(".xlsx"):
            raise ExcelUpdateError(
                code=40001,
                http_status=400,
                message="invalid request",
                error={"field": "file", "reason": "only .xlsx is supported"},
            )
        if not payload:
            raise ExcelUpdateError(
                code=40001,
                http_status=400,
                message="invalid request",
                error={"field": "file", "reason": "empty file"},
            )

    @staticmethod
    def _build_operation_no() -> str:
        return f"OP{uuid4().hex[:12].upper()}"

    @staticmethod
    def _ensure_task_exists(repo: ExcelUpdateRepository, task_id: int) -> None:
        if repo.get_task(task_id) is None:
            raise ExcelUpdateError(code=40004, http_status=404, message="task not found")

    def _build_version_info(
        self,
        version,
        *,
        include_download: bool,
        base_url: str | None = None,
    ) -> VersionInfoData:
        if version is None:
            raise ExcelUpdateError(code=40004, http_status=404, message="version not found")
        download_url = None
        if include_download and base_url is not None:
            download_url = self._build_download_url(
                base_url=base_url,
                object_key=version.object_key,
                file_name=version.file_name,
            )
        return VersionInfoData(
            version_id=version.id,
            version_no=version.version_no,
            file_name=version.file_name,
            file_size=version.file_size,
            is_current=bool(version.is_current),
            source_operation_id=version.source_operation_id,
            created_at=to_iso8601(version.created_at),
            download_url=download_url,
        )

    def _build_download_data(self, *, task_id: int, version, base_url: str) -> DownloadUrlData:
        return DownloadUrlData(
            task_id=task_id,
            version_id=version.id,
            version_no=version.version_no,
            file_name=version.file_name,
            download_url=self._build_download_url(
                base_url=base_url,
                object_key=version.object_key,
                file_name=version.file_name,
            ),
        )

    @staticmethod
    def _build_download_url(*, base_url: str, object_key: str, file_name: str) -> str:
        token = encode_download_token(object_key=object_key, file_name=file_name)
        return f"{base_url.rstrip('/')}/api/excel-tasks/files/{token}"

    @contextmanager
    def _session_scope(self):
        db = SessionLocal()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
