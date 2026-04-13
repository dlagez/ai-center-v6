from typing import Any

from src.workflow.excel_update.schemas import ExcelUpdateChange, ExcelUpdateError, ExcelUpdateRequest


def apply_excel_updates(
    request: ExcelUpdateRequest,
    parsed_template: dict[str, Any],
    records: list[dict[str, Any]],
) -> tuple[list[ExcelUpdateChange], list[ExcelUpdateError], list[str]]:
    worksheet = parsed_template["worksheet"]
    row_index_by_match_value: dict[str, int] = parsed_template["row_index_by_match_value"]
    target_column_index: int = parsed_template["target_column_index"]
    duplicate_match_values: list[str] = parsed_template.get("duplicate_match_values", [])

    changes: list[ExcelUpdateChange] = []
    errors: list[ExcelUpdateError] = [
        ExcelUpdateError(
            code="DUPLICATE_MATCH_KEY",
            message="Duplicate match key found in Excel sheet.",
            match_value=match_value,
        )
        for match_value in duplicate_match_values
    ]
    unmatched_keys: list[str] = []

    for record in records:
        match_value_raw = record.get(request.match_field)
        if match_value_raw in (None, ""):
            errors.append(
                ExcelUpdateError(
                    code="MISSING_MATCH_KEY",
                    message=f"Business record missing '{request.match_field}'.",
                    details={"record": record},
                )
            )
            continue

        match_value = str(match_value_raw).strip()
        row_index = row_index_by_match_value.get(match_value)
        if row_index is None:
            unmatched_keys.append(match_value)
            continue

        new_value = record.get("value")
        if new_value is None:
            errors.append(
                ExcelUpdateError(
                    code="MISSING_VALUE",
                    message="Business record missing 'value'.",
                    match_value=match_value,
                    details={"record": record},
                )
            )
            continue

        cell = worksheet.cell(row=row_index, column=target_column_index)
        old_value = cell.value
        if old_value == new_value:
            continue
        if old_value not in (None, "") and not request.overwrite_existing:
            errors.append(
                ExcelUpdateError(
                    code="OVERWRITE_SKIPPED",
                    message="Target cell already has a value and overwrite is disabled.",
                    match_value=match_value,
                    details={
                        "row_index": row_index,
                        "column_name": request.target_column,
                        "old_value": old_value,
                    },
                )
            )
            continue

        cell.value = new_value
        changes.append(
            ExcelUpdateChange(
                match_value=match_value,
                row_index=row_index,
                column_name=request.target_column,
                old_value=old_value,
                new_value=new_value,
            )
        )

    return changes, errors, unmatched_keys
