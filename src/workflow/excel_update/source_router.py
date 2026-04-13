from typing import Any

from src.workflow.excel_update.api_utils import fetch_pm_records
from src.workflow.excel_update.excel_source import fetch_excel_records
from src.workflow.excel_update.schemas import ExcelUpdateRequest


def fetch_records_by_source(request: ExcelUpdateRequest) -> list[dict[str, Any]]:
    if request.source_type == "pm_api":
        return fetch_pm_records(request)
    if request.source_type == "excel_file":
        return fetch_excel_records(request)
    raise ValueError(f"Unsupported source_type: {request.source_type}")
