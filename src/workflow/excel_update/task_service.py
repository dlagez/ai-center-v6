from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from src.db.session import SessionLocal, get_engine
from src.storage.file_service import get_file_service
from src.workflow.excel_update.analyzer import analyze_excel_update
from src.workflow.excel_update.models import ExcelUpdateOperation, ExcelUpdateTask
from src.workflow.excel_update.repository import ExcelUpdateTaskRepository
from src.workflow.excel_update.schemas import (
    ExcelUpdateAnalysisResult,
    ExcelUpdateOperationCreate,
    ExcelUpdateOperationResult,
    ExcelUpdateRequest,
    ExcelUpdateResult,
    ExcelUpdateTaskDetail,
    ExcelUpdateTaskSummary,
)
from src.workflow.excel_update.service import ExcelUpdateService


class ExcelUpdateTaskService:
    def __init__(self, workflow_service: ExcelUpdateService | None = None) -> None:
        self.workflow_service = workflow_service or ExcelUpdateService()
        self.file_service = get_file_service()
        get_engine()

    def create_task(self, source_excel_path: str, uploaded_file_name: str) -> ExcelUpdateTaskDetail:
        task_id = f"excel_update_{uuid4().hex}"
        now = datetime.now()
        stored_source_path = source_excel_path
        stored_source_name = self._build_source_name(uploaded_file_name)

        task = ExcelUpdateTaskDetail(
            task_id=task_id,
            file_name=uploaded_file_name,
            created_at=now,
            updated_at=now,
            operation_count=0,
            latest_target_column=None,
            latest_output_file_name=stored_source_name,
            detail_url=f"/workflow/excel-update/tasks/{task_id}",
            download_url=f"/workflow/excel-update/tasks/{task_id}/file",
            source_excel_path=str(stored_source_path),
            current_excel_path=str(stored_source_path),
            operations=[],
        )
        with SessionLocal() as db:
            repository = ExcelUpdateTaskRepository(db)
            repository.create_task(self._to_task_entity(task))
        return task

    def list_tasks(self) -> list[ExcelUpdateTaskSummary]:
        with SessionLocal() as db:
            repository = ExcelUpdateTaskRepository(db)
            return [self._to_task_summary(item) for item in repository.list_tasks()]

    def get_task(self, task_id: str) -> ExcelUpdateTaskDetail:
        with SessionLocal() as db:
            repository = ExcelUpdateTaskRepository(db)
            task = repository.get_task(task_id)
        if task is None:
            raise FileNotFoundError(f"Excel update task not found: {task_id}")
        return self._to_task_detail(task)

    def run_operation(self, task_id: str, operation: ExcelUpdateOperationCreate) -> ExcelUpdateOperationResult:
        task = self.get_task(task_id)
        with TemporaryDirectory(prefix=f"{task_id}_") as tmp_dir:
            working_dir = Path(tmp_dir)
            task_excel_path = self._download_object_to_path(
                task.current_excel_path,
                working_dir / self._build_source_name(task.file_name),
            )
            source_excel_path = self._download_optional_object_to_path(
                operation.source_excel_path,
                working_dir / self._build_source_name("source.xlsx"),
            )

            local_operation = operation.model_copy(update={"source_excel_path": source_excel_path})
            analysis = self._resolve_analysis(str(task_excel_path), local_operation)

            target_column = operation.target_column or (analysis.target_column if analysis else None)
            if not target_column:
                raise ValueError("target_column is required")

            output_file_name = self._build_operation_output_name(
                task.file_name,
                len(task.operations) + 1,
                target_column,
            )
            local_output_path = working_dir / output_file_name

            request = ExcelUpdateRequest(
                excel_path=str(task_excel_path),
                source_type=operation.source_type,
                user_prompt=operation.user_prompt,
                sheet_name=operation.sheet_name or (analysis.sheet_name if analysis else None),
                match_column=operation.match_column or (analysis.match_column if analysis else "项目编号"),
                match_field=operation.match_field or (analysis.match_field if analysis else "project_no"),
                source_excel_path=source_excel_path,
                source_sheet_name=operation.source_sheet_name or (analysis.source_sheet_name if analysis else None),
                source_match_column=operation.source_match_column or (analysis.source_match_column if analysis else None) or "项目编号",
                source_value_column=operation.source_value_column or (analysis.source_value_column if analysis else None),
                target_column=target_column,
                query_conditions=operation.query_conditions or (analysis.query_conditions if analysis else []),
                output_path=str(local_output_path),
                overwrite_existing=operation.overwrite_existing,
                operator=operation.operator,
            )

            result = self.workflow_service.run(request)
            result_object_name = self._upload_local_file(
                local_output_path,
                self._build_storage_object_name(task_id, output_file_name),
            )
            persisted_request = request.model_copy(
                update={
                    "excel_path": task.current_excel_path,
                    "source_excel_path": operation.source_excel_path,
                    "output_path": result_object_name,
                }
            )
            result = result.model_copy(
                update={
                    "excel_path": task.current_excel_path,
                    "output_path": result_object_name,
                }
            )

        operation_id = f"operation_{uuid4().hex}"
        operation_result = ExcelUpdateOperationResult(
            operation_id=operation_id,
            sequence=len(task.operations) + 1,
            created_at=datetime.now(),
            output_file_name=output_file_name,
            download_url=f"/workflow/excel-update/tasks/{task_id}/operations/{operation_id}/file",
            detail_url=f"/workflow/excel-update/tasks/{task_id}",
            request=persisted_request,
            analysis=analysis,
            result=result,
        )

        task.operations.append(operation_result)
        task.operation_count = len(task.operations)
        task.updated_at = operation_result.created_at
        task.latest_target_column = request.target_column
        task.latest_output_file_name = operation_result.output_file_name
        task.current_excel_path = result.output_path or task.current_excel_path
        with SessionLocal() as db:
            repository = ExcelUpdateTaskRepository(db)
            task_entity = repository.get_task(task_id)
            if task_entity is None:
                raise FileNotFoundError(f"Excel update task not found: {task_id}")
            task_entity.updated_at = task.updated_at
            task_entity.operation_count = task.operation_count
            task_entity.latest_target_column = task.latest_target_column
            task_entity.latest_output_file_name = task.latest_output_file_name
            task_entity.current_excel_path = task.current_excel_path
            operation_entity = self._to_operation_entity(task_id, operation_result)
            repository.add_operation(task_entity, operation_entity)
        return operation_result

    def get_output_file_content(self, task_id: str) -> bytes:
        task = self.get_task(task_id)
        return self._download_object(task.current_excel_path)

    def get_operation_output_file_content(self, task_id: str, operation_id: str) -> bytes:
        task = self.get_task(task_id)
        operation = next((item for item in task.operations if item.operation_id == operation_id), None)
        if operation is None:
            raise FileNotFoundError(f"Excel update operation not found: {operation_id}")
        output_object_name = operation.result.output_path or ""
        if not output_object_name:
            raise FileNotFoundError(
                f"Excel update output file not found for task: {task_id}, operation: {operation_id}"
            )
        return self._download_object(output_object_name)

    def _resolve_analysis(
        self,
        excel_path: str,
        operation: ExcelUpdateOperationCreate,
    ) -> ExcelUpdateAnalysisResult | None:
        has_prompt = bool((operation.user_prompt or "").strip())
        missing_target_fields = not all([operation.sheet_name, operation.target_column])

        if operation.source_type == "excel_file":
            missing_source_fields = not all([operation.source_match_column, operation.source_value_column])
            missing_fields = missing_target_fields or missing_source_fields
        else:
            missing_pm_fields = not all([operation.match_column, operation.match_field, operation.query_conditions])
            missing_fields = missing_target_fields or missing_pm_fields

        if not has_prompt or not missing_fields:
            return None

        return analyze_excel_update(
            excel_path,
            operation.user_prompt or "",
            source_excel_path=operation.source_excel_path,
        )

    @staticmethod
    def _build_source_name(uploaded_file_name: str) -> str:
        source = Path(uploaded_file_name)
        if source.suffix:
            return f"{source.stem}_source{source.suffix}"
        return f"{uploaded_file_name}_source.xlsx"

    @staticmethod
    def _sanitize_name(value: str) -> str:
        cleaned = "".join(char if char.isalnum() else "_" for char in value.strip())
        cleaned = "_".join(part for part in cleaned.split("_") if part)
        return cleaned or "column"

    def _build_operation_output_name(self, uploaded_file_name: str, sequence: int, target_column: str) -> str:
        source = Path(uploaded_file_name)
        suffix = source.suffix or ".xlsx"
        safe_target = self._sanitize_name(target_column)
        return f"{source.stem}_step_{sequence:02d}_{safe_target}{suffix}"

    @staticmethod
    def _build_storage_object_name(task_id: str, file_name: str) -> str:
        return f"excel-update/{task_id}/{Path(file_name).name}"

    def _download_object(self, object_name: str) -> bytes:
        try:
            return self.file_service.download_file(object_name)
        except Exception as exc:
            raise FileNotFoundError(f"Excel update file not found in storage: {object_name}") from exc

    def _download_object_to_path(self, object_name: str, destination: Path) -> Path:
        payload = self._download_object(object_name)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(payload)
        return destination

    def _download_optional_object_to_path(self, object_name: str | None, destination: Path) -> str | None:
        if not object_name:
            return None
        return str(self._download_object_to_path(object_name, destination))

    def _upload_local_file(self, file_path: Path, object_name: str) -> str:
        with file_path.open("rb") as stream:
            self.file_service.upload_file(
                stream,
                object_name=object_name,
            )
        return object_name

    @staticmethod
    def _to_task_entity(payload: ExcelUpdateTaskDetail) -> ExcelUpdateTask:
        return ExcelUpdateTask(
            task_id=payload.task_id,
            file_name=payload.file_name,
            created_at=payload.created_at,
            updated_at=payload.updated_at,
            operation_count=payload.operation_count,
            latest_target_column=payload.latest_target_column,
            latest_output_file_name=payload.latest_output_file_name,
            detail_url=payload.detail_url,
            download_url=payload.download_url,
            source_excel_path=payload.source_excel_path,
            current_excel_path=payload.current_excel_path,
        )

    @staticmethod
    def _to_operation_entity(task_id: str, payload: ExcelUpdateOperationResult) -> ExcelUpdateOperation:
        analysis_payload = payload.analysis.model_dump(mode="json") if payload.analysis else None
        return ExcelUpdateOperation(
            operation_id=payload.operation_id,
            task_id=task_id,
            sequence=payload.sequence,
            created_at=payload.created_at,
            output_file_name=payload.output_file_name,
            download_url=payload.download_url,
            detail_url=payload.detail_url,
            request_payload=payload.request.model_dump(mode="json"),
            analysis_payload=analysis_payload,
            result_payload=payload.result.model_dump(mode="json"),
        )

    @staticmethod
    def _to_task_summary(entity: ExcelUpdateTask) -> ExcelUpdateTaskSummary:
        return ExcelUpdateTaskSummary(
            task_id=entity.task_id,
            file_name=entity.file_name,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            operation_count=entity.operation_count,
            latest_target_column=entity.latest_target_column,
            latest_output_file_name=entity.latest_output_file_name,
            detail_url=entity.detail_url,
            download_url=entity.download_url,
        )

    @staticmethod
    def _to_task_detail(entity: ExcelUpdateTask) -> ExcelUpdateTaskDetail:
        return ExcelUpdateTaskDetail(
            task_id=entity.task_id,
            file_name=entity.file_name,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            operation_count=entity.operation_count,
            latest_target_column=entity.latest_target_column,
            latest_output_file_name=entity.latest_output_file_name,
            detail_url=entity.detail_url,
            download_url=entity.download_url,
            source_excel_path=entity.source_excel_path,
            current_excel_path=entity.current_excel_path,
            operations=[ExcelUpdateTaskService._to_operation_result(item) for item in entity.operations],
        )

    @staticmethod
    def _to_operation_result(entity: ExcelUpdateOperation) -> ExcelUpdateOperationResult:
        analysis = (
            ExcelUpdateAnalysisResult.model_validate(entity.analysis_payload)
            if entity.analysis_payload is not None
            else None
        )
        return ExcelUpdateOperationResult(
            operation_id=entity.operation_id,
            sequence=entity.sequence,
            created_at=entity.created_at,
            output_file_name=entity.output_file_name,
            download_url=entity.download_url,
            detail_url=entity.detail_url,
            request=ExcelUpdateRequest.model_validate(entity.request_payload),
            analysis=analysis,
            result=ExcelUpdateResult.model_validate(entity.result_payload),
        )
