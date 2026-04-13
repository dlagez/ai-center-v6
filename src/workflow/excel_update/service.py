from collections.abc import Callable
from typing import Any

from src.workflow.excel_update.exporter import export_updated_workbook, resolve_output_path
from src.workflow.excel_update.parser import parse_excel_template
from src.workflow.excel_update.schemas import ExcelUpdateRequest, ExcelUpdateResult, ExcelUpdateSummary
from src.workflow.excel_update.source_router import fetch_records_by_source
from src.workflow.excel_update.updater import apply_excel_updates


class ExcelUpdateService:
    def __init__(
        self,
        fetcher: Callable[[ExcelUpdateRequest], list[dict[str, Any]]] | None = None,
        parser: Callable[[ExcelUpdateRequest], dict[str, Any]] | None = None,
        updater: Callable[
            [ExcelUpdateRequest, dict[str, Any], list[dict[str, Any]]],
            tuple[list[Any], list[Any], list[str]],
        ]
        | None = None,
    ) -> None:
        self.fetcher = fetcher or fetch_records_by_source
        self.parser = parser or parse_excel_template
        self.updater = updater or apply_excel_updates

    def run(self, request: ExcelUpdateRequest) -> ExcelUpdateResult:
        parsed_template = self.parser(request)
        records = self.fetcher(request)
        changes, errors, unmatched_keys = self.updater(request, parsed_template, records)
        output_path = export_updated_workbook(request, parsed_template, resolve_output_path(request))

        matched_records = max(len(records) - len(unmatched_keys), 0)
        summary = ExcelUpdateSummary(
            total_records=len(records),
            matched_records=matched_records,
            updated_cells=len(changes),
            skipped_records=0,
            unmatched_records=len(unmatched_keys),
            error_count=len(errors),
        )

        return ExcelUpdateResult(
            excel_path=request.excel_path,
            output_path=output_path,
            sheet_name=parsed_template.get("sheet_name"),
            match_column=request.match_column,
            match_field=request.match_field,
            records=records,
            changes=changes,
            errors=errors,
            unmatched_keys=unmatched_keys,
            summary=summary,
        )
