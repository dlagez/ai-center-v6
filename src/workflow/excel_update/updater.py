from typing import Any

from src.workflow.excel_update.schemas import ExcelUpdateChange, ExcelUpdateError, ExcelUpdateRequest


def apply_excel_updates(
    request: ExcelUpdateRequest,
    parsed_template: dict[str, Any],
    records: list[dict[str, Any]],
) -> tuple[list[ExcelUpdateChange], list[ExcelUpdateError], list[str]]:
    """
    Placeholder updater.

    A real implementation should match each record to an Excel row and write
    mapped fields into their target columns.
    """
    _ = (request, parsed_template, records)
    return [], [], []
