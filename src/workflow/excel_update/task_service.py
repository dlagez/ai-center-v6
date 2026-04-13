import json
import shutil
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from src.config.settings import settings
from src.workflow.excel_update.analyzer import analyze_excel_update
from src.workflow.excel_update.schemas import (
    ExcelUpdateAnalysisResult,
    ExcelUpdateOperationCreate,
    ExcelUpdateOperationResult,
    ExcelUpdateRequest,
    ExcelUpdateTaskDetail,
    ExcelUpdateTaskSummary,
)
from src.workflow.excel_update.service import ExcelUpdateService


class ExcelUpdateTaskService:
    def __init__(self, workflow_service: ExcelUpdateService | None = None) -> None:
        self.workflow_service = workflow_service or ExcelUpdateService()
        self.base_dir = Path(settings.excel_update_output_dir).expanduser().resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def create_task(self, source_excel_path: str, uploaded_file_name: str) -> ExcelUpdateTaskDetail:
        task_id = f"excel_update_{uuid4().hex}"
        now = datetime.now()
        task_dir = self.base_dir / task_id
        task_dir.mkdir(parents=True, exist_ok=True)

        source_path = Path(source_excel_path)
        stored_source_path = task_dir / self._build_source_name(uploaded_file_name)
        shutil.copy2(source_path, stored_source_path)

        task = ExcelUpdateTaskDetail(
            task_id=task_id,
            file_name=uploaded_file_name,
            created_at=now,
            updated_at=now,
            operation_count=0,
            latest_target_column=None,
            latest_output_file_name=stored_source_path.name,
            detail_url=f"/workflow/excel-update/tasks/{task_id}",
            download_url=f"/workflow/excel-update/tasks/{task_id}/file",
            source_excel_path=str(stored_source_path),
            current_excel_path=str(stored_source_path),
            operations=[],
        )
        self._save_task(task)
        return task

    def list_tasks(self) -> list[ExcelUpdateTaskSummary]:
        tasks: list[ExcelUpdateTaskSummary] = []
        for task_dir in sorted(self.base_dir.glob("excel_update_*"), reverse=True):
            result_path = task_dir / "result.json"
            if not result_path.is_file():
                continue
            payload = json.loads(result_path.read_text(encoding="utf-8"))
            task = ExcelUpdateTaskDetail.model_validate(payload)
            tasks.append(
                ExcelUpdateTaskSummary(
                    task_id=task.task_id,
                    file_name=task.file_name,
                    created_at=task.created_at,
                    updated_at=task.updated_at,
                    operation_count=task.operation_count,
                    latest_target_column=task.latest_target_column,
                    latest_output_file_name=task.latest_output_file_name,
                    detail_url=task.detail_url,
                    download_url=task.download_url,
                )
            )
        return tasks

    def get_task(self, task_id: str) -> ExcelUpdateTaskDetail:
        task_dir = self.base_dir / task_id
        result_path = task_dir / "result.json"
        if not result_path.is_file():
            raise FileNotFoundError(f"Excel update task not found: {task_id}")

        payload = json.loads(result_path.read_text(encoding="utf-8"))
        return ExcelUpdateTaskDetail.model_validate(payload)

    def run_operation(self, task_id: str, operation: ExcelUpdateOperationCreate) -> ExcelUpdateOperationResult:
        task = self.get_task(task_id)
        analysis = self._resolve_analysis(task.current_excel_path, operation)

        target_column = operation.target_column or (analysis.target_column if analysis else None)
        if not target_column:
            raise ValueError("target_column is required")

        request = ExcelUpdateRequest(
            excel_path=task.current_excel_path,
            source_type=operation.source_type,
            user_prompt=operation.user_prompt,
            sheet_name=operation.sheet_name or (analysis.sheet_name if analysis else None),
            match_column=operation.match_column or (analysis.match_column if analysis else "项目编号"),
            match_field=operation.match_field or (analysis.match_field if analysis else "project_no"),
            source_excel_path=operation.source_excel_path,
            source_sheet_name=operation.source_sheet_name or (analysis.source_sheet_name if analysis else None),
            source_match_column=operation.source_match_column or (analysis.source_match_column if analysis else None) or "项目编号",
            source_value_column=operation.source_value_column or (analysis.source_value_column if analysis else None),
            target_column=target_column,
            query_conditions=operation.query_conditions or (analysis.query_conditions if analysis else []),
            output_path=str(
                self.base_dir
                / task_id
                / self._build_operation_output_name(task.file_name, len(task.operations) + 1, target_column)
            ),
            overwrite_existing=operation.overwrite_existing,
            operator=operation.operator,
        )

        result = self.workflow_service.run(request)
        operation_id = f"operation_{uuid4().hex}"
        operation_result = ExcelUpdateOperationResult(
            operation_id=operation_id,
            sequence=len(task.operations) + 1,
            created_at=datetime.now(),
            output_file_name=Path(result.output_path or "").name,
            download_url=f"/workflow/excel-update/tasks/{task_id}/operations/{operation_id}/file",
            detail_url=f"/workflow/excel-update/tasks/{task_id}",
            request=request,
            analysis=analysis,
            result=result,
        )

        task.operations.append(operation_result)
        task.operation_count = len(task.operations)
        task.updated_at = operation_result.created_at
        task.latest_target_column = request.target_column
        task.latest_output_file_name = operation_result.output_file_name
        task.current_excel_path = result.output_path or task.current_excel_path
        self._save_task(task)
        return operation_result

    def get_output_file_path(self, task_id: str) -> Path:
        task = self.get_task(task_id)
        output_path = Path(task.current_excel_path)
        if not output_path.is_file():
            raise FileNotFoundError(f"Excel update output file not found for task: {task_id}")
        return output_path

    def get_operation_output_file_path(self, task_id: str, operation_id: str) -> Path:
        task = self.get_task(task_id)
        operation = next((item for item in task.operations if item.operation_id == operation_id), None)
        if operation is None:
            raise FileNotFoundError(f"Excel update operation not found: {operation_id}")

        output_path = Path(operation.result.output_path or "")
        if not output_path.is_file():
            raise FileNotFoundError(
                f"Excel update output file not found for task: {task_id}, operation: {operation_id}"
            )
        return output_path

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

    def _save_task(self, payload: ExcelUpdateTaskDetail) -> None:
        path = self.base_dir / payload.task_id / "result.json"
        path.write_text(
            json.dumps(payload.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
