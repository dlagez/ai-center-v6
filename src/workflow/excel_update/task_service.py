import json
from pathlib import Path
from uuid import uuid4

from src.config.settings import settings
from src.workflow.excel_update.schemas import (
    ExcelUpdateRequest,
    ExcelUpdateResult,
    ExcelUpdateTaskResult,
)
from src.workflow.excel_update.service import ExcelUpdateService


class ExcelUpdateTaskService:
    def __init__(self, workflow_service: ExcelUpdateService | None = None) -> None:
        self.workflow_service = workflow_service or ExcelUpdateService()
        self.base_dir = Path(settings.excel_update_output_dir).expanduser().resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def create_task(
        self,
        request: ExcelUpdateRequest,
        uploaded_file_name: str,
    ) -> ExcelUpdateTaskResult:
        task_id = f"excel_update_{uuid4().hex}"
        task_dir = self.base_dir / task_id
        task_dir.mkdir(parents=True, exist_ok=True)

        result = self.workflow_service.run(
            request.model_copy(
                update={
                    "output_path": str(task_dir / self._build_output_name(uploaded_file_name)),
                }
            )
        )

        task_result = ExcelUpdateTaskResult(
            task_id=task_id,
            file_name=uploaded_file_name,
            output_file_name=Path(result.output_path or "").name,
            download_url=f"/workflow/excel-update/tasks/{task_id}/file",
            detail_url=f"/workflow/excel-update/tasks/{task_id}",
            result=result,
        )
        self._save_metadata(task_dir / "result.json", task_result)
        return task_result

    def get_task(self, task_id: str) -> ExcelUpdateTaskResult:
        task_dir = self.base_dir / task_id
        result_path = task_dir / "result.json"
        if not result_path.is_file():
            raise FileNotFoundError(f"Excel update task not found: {task_id}")

        payload = json.loads(result_path.read_text(encoding="utf-8"))
        return ExcelUpdateTaskResult.model_validate(payload)

    def get_output_file_path(self, task_id: str) -> Path:
        task = self.get_task(task_id)
        output_path = Path(task.result.output_path or "")
        if not output_path.is_file():
            raise FileNotFoundError(f"Excel update output file not found for task: {task_id}")
        return output_path

    @staticmethod
    def _build_output_name(uploaded_file_name: str) -> str:
        source = Path(uploaded_file_name)
        if source.suffix:
            return f"{source.stem}_updated{source.suffix}"
        return f"{uploaded_file_name}_updated.xlsx"

    @staticmethod
    def _save_metadata(path: Path, payload: ExcelUpdateTaskResult) -> None:
        path.write_text(
            json.dumps(payload.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
