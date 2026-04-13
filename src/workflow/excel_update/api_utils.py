from typing import Any

from src.workflow.excel_update.schemas import ExcelUpdateQueryCondition, ExcelUpdateRequest


def build_query_dict(conditions: list[ExcelUpdateQueryCondition]) -> dict[str, Any]:
    return {condition.key: condition.value for condition in conditions}


def fetch_pm_records(request: ExcelUpdateRequest) -> list[dict[str, Any]]:
    """
    Default placeholder PM fetcher.

    Replace this function with a real PM API client when integration is ready.
    """
    _ = build_query_dict(request.query_conditions)
    return [
        {
            "project_no": "HKZC-N-YW-2021-001",
            "value": 20,
        },
        {
            "project_no": "HKZC-N-YW-2021-002",
            "value": 30,
        },
    ]
