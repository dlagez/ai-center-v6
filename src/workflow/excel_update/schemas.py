from typing import Any

from pydantic import BaseModel, Field


class ExcelUpdateQueryCondition(BaseModel):
    key: str = Field(..., description="Query condition key sent to the business system.")
    value: Any = Field(..., description="Query condition value.")


class ExcelUpdateFieldMapping(BaseModel):
    source_field: str = Field(..., description="Field name from the business system record.")
    target_column: str | None = Field(
        default=None,
        description="Explicit Excel column header to write into when already known.",
    )


class ExcelUpdateRequest(BaseModel):
    excel_path: str = Field(..., description="Local Excel file path.")
    sheet_name: str | None = Field(default=None, description="Target sheet name.")
    match_key: str = Field(
        default="project_no",
        description="Business key used to match records with Excel rows.",
    )
    query_conditions: list[ExcelUpdateQueryCondition] = Field(
        default_factory=list,
        description="Conditions used when fetching records from the business system.",
    )
    field_mappings: list[ExcelUpdateFieldMapping] = Field(
        default_factory=list,
        description="Source-to-target field mappings for Excel updates.",
    )
    output_path: str | None = Field(
        default=None,
        description="Optional output path for the updated Excel file.",
    )
    overwrite_existing: bool = Field(
        default=True,
        description="Whether matched cells may overwrite existing values.",
    )
    operator: str | None = Field(default=None, description="Operator or task initiator identifier.")


class ExcelUpdateChange(BaseModel):
    match_value: str = Field(..., description="Matched business key value.")
    row_index: int = Field(..., description="One-based Excel row index.")
    column_name: str = Field(..., description="Excel target column name.")
    old_value: Any = Field(default=None, description="Previous cell value.")
    new_value: Any = Field(default=None, description="Updated cell value.")


class ExcelUpdateError(BaseModel):
    code: str = Field(..., description="Stable error code.")
    message: str = Field(..., description="Human-readable error message.")
    match_value: str | None = Field(default=None, description="Business key related to the error.")
    details: dict[str, Any] = Field(default_factory=dict, description="Structured error details.")


class ExcelUpdateSummary(BaseModel):
    total_records: int = Field(default=0, description="Records fetched from the business system.")
    matched_records: int = Field(default=0, description="Records matched to Excel rows.")
    updated_cells: int = Field(default=0, description="Total Excel cells updated.")
    skipped_records: int = Field(default=0, description="Records skipped during processing.")
    unmatched_records: int = Field(default=0, description="Records that found no matching row.")
    error_count: int = Field(default=0, description="Total processing errors.")


class ExcelUpdateResult(BaseModel):
    excel_path: str = Field(..., description="Original Excel file path.")
    output_path: str | None = Field(default=None, description="Updated Excel file path when produced.")
    sheet_name: str | None = Field(default=None, description="Resolved target sheet name.")
    match_key: str = Field(..., description="Business key used for matching.")
    records: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Fetched business records used in this run.",
    )
    changes: list[ExcelUpdateChange] = Field(
        default_factory=list,
        description="Applied Excel changes.",
    )
    errors: list[ExcelUpdateError] = Field(
        default_factory=list,
        description="Structured processing errors.",
    )
    unmatched_keys: list[str] = Field(
        default_factory=list,
        description="Business keys not found in the Excel sheet.",
    )
    summary: ExcelUpdateSummary = Field(
        default_factory=ExcelUpdateSummary,
        description="Execution summary for the batch update.",
    )


class ExcelUpdateTaskResult(BaseModel):
    task_id: str = Field(..., description="Unique task identifier.")
    file_name: str = Field(..., description="Uploaded source file name.")
    output_file_name: str = Field(..., description="Generated output file name.")
    download_url: str = Field(..., description="API path used to download the output Excel file.")
    detail_url: str = Field(..., description="API path used to fetch task details.")
    result: ExcelUpdateResult = Field(..., description="Structured execution result.")
