from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ExcelUpdateQueryCondition(BaseModel):
    key: str = Field(..., description="Query condition key sent to the business system.")
    value: Any = Field(..., description="Query condition value.")


class ExcelUpdateRequest(BaseModel):
    excel_path: str = Field(..., description="Local Excel file path.")
    user_prompt: str | None = Field(
        default=None,
        description="Natural-language prompt used to infer update parameters.",
    )
    sheet_name: str | None = Field(default=None, description="Target sheet name.")
    match_column: str = Field(
        default="项目编号",
        description="Excel column header used to locate project rows.",
    )
    match_field: str = Field(
        default="project_no",
        description="Business record field used to match the Excel project column.",
    )
    query_conditions: list[ExcelUpdateQueryCondition] = Field(
        default_factory=list,
        description="Conditions used when fetching records from the business system.",
    )
    target_column: str = Field(
        ...,
        description="Excel target column header that receives the business value.",
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
    match_column: str = Field(..., description="Excel column header used for matching.")
    match_field: str = Field(..., description="Business record field used for matching.")
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


class ExcelSheetAnalysis(BaseModel):
    sheet_name: str = Field(..., description="Worksheet name.")
    header_candidates: list[str] = Field(
        default_factory=list,
        description="Detected non-empty header texts from the top scan window.",
    )


class ExcelUpdateAnalysisResult(BaseModel):
    user_prompt: str = Field(..., description="Original natural-language prompt.")
    sheet_name: str | None = Field(default=None, description="Resolved target sheet name.")
    match_column: str = Field(..., description="Resolved Excel match column.")
    match_field: str = Field(..., description="Resolved business match field.")
    target_column: str | None = Field(default=None, description="Resolved target Excel column.")
    query_conditions: list[ExcelUpdateQueryCondition] = Field(
        default_factory=list,
        description="Structured business query conditions inferred from the prompt.",
    )
    sheet_options: list[ExcelSheetAnalysis] = Field(
        default_factory=list,
        description="Worksheet summaries used during analysis.",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Non-fatal analysis warnings that may require user confirmation.",
    )


class ExcelUpdateOperationCreate(BaseModel):
    user_prompt: str | None = None
    sheet_name: str | None = None
    match_column: str | None = None
    match_field: str | None = None
    target_column: str | None = None
    query_conditions: list[ExcelUpdateQueryCondition] = Field(default_factory=list)
    overwrite_existing: bool = True
    operator: str | None = None


class ExcelUpdateOperationResult(BaseModel):
    operation_id: str
    sequence: int
    created_at: datetime
    output_file_name: str
    download_url: str
    detail_url: str
    request: ExcelUpdateRequest
    analysis: ExcelUpdateAnalysisResult | None = None
    result: ExcelUpdateResult


class ExcelUpdateTaskSummary(BaseModel):
    task_id: str
    file_name: str
    created_at: datetime
    updated_at: datetime
    operation_count: int = 0
    latest_target_column: str | None = None
    latest_output_file_name: str
    detail_url: str
    download_url: str


class ExcelUpdateTaskDetail(ExcelUpdateTaskSummary):
    source_excel_path: str
    current_excel_path: str
    operations: list[ExcelUpdateOperationResult] = Field(default_factory=list)


ExcelUpdateTaskResult = ExcelUpdateTaskDetail
