from collections.abc import Callable
from typing import Any

from src.workflow.excel_update.schemas import ExcelUpdateQueryCondition, ExcelUpdateRequest


BusinessRecordFetcher = Callable[[ExcelUpdateRequest], list[dict[str, Any]]]


def build_query_dict(conditions: list[ExcelUpdateQueryCondition]) -> dict[str, Any]:
    return {condition.key: condition.value for condition in conditions}


def fetch_business_records(request: ExcelUpdateRequest) -> list[dict[str, Any]]:
    """
    Default placeholder fetcher.

    Replace this function with a business API client, or inject a custom fetcher
    into ExcelUpdateService for integration tests and runtime wiring.
    """
    _ = build_query_dict(request.query_conditions)
    return []
