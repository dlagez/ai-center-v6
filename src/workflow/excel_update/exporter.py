from pathlib import Path

from src.workflow.excel_update.schemas import ExcelUpdateRequest


def resolve_output_path(request: ExcelUpdateRequest) -> str:
    if request.output_path:
        return request.output_path

    source = Path(request.excel_path)
    if source.suffix:
        return str(source.with_name(f"{source.stem}_updated{source.suffix}"))
    return f"{request.excel_path}_updated"


def export_updated_workbook(
    request: ExcelUpdateRequest,
    parsed_template: dict,
    output_path: str,
) -> str:
    workbook = parsed_template["workbook"]
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(target)
    return str(target)
