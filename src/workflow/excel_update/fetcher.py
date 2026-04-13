from typing import Any

from src.workflow.excel_update.api_utils import build_query_dict, fetch_pm_records
from src.workflow.excel_update.schemas import ExcelUpdateRequest

def fetch_business_records(request: ExcelUpdateRequest) -> list[dict[str, Any]]:
    return fetch_pm_records(request)


__all__ = ["build_query_dict", "fetch_business_records"]
