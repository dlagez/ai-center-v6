from pathlib import Path
from typing import Any

from src.workflow.excel_update.schemas import ExcelUpdateRequest


def parse_excel_template(request: ExcelUpdateRequest) -> dict[str, Any]:
    """
    Placeholder parser that resolves the basic sheet context.

    A real implementation should load the workbook, identify the target sheet,
    build a header map, and locate the match-key column.
    """
    excel_path = Path(request.excel_path)
    if not excel_path.is_file():
        raise FileNotFoundError(f"Excel file not found: {request.excel_path}")

    return {
        "excel_path": request.excel_path,
        "sheet_name": request.sheet_name,
        "match_key": request.match_key,
        "field_mappings": request.field_mappings,
    }
