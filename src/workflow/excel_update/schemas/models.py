from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class ApiSuccessResponse(BaseModel):
    code: int = 0
    message: str = "ok"
    data: Any = None


class ApiErrorResponse(BaseModel):
    code: int
    message: str
    error: dict[str, Any] | None = None


class OperationUpdateItem(BaseModel):
    match_value: str = Field(..., description="Value used to locate the target row.")
    target_value: str | int | float | None = Field(default=None, description="Value written to the target cell.")

    @field_validator("match_value")
    @classmethod
    def validate_match_value(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("match_value cannot be blank")
        return stripped


class CreateOperationRequest(BaseModel):
    sheet_name: str = Field(..., min_length=1, max_length=255)
    match_column: str = Field(..., min_length=1, max_length=16)
    target_column: str = Field(..., min_length=1, max_length=16)
    updates: list[OperationUpdateItem] = Field(..., min_length=1, max_length=1000)
    submitted_by: str | None = Field(default=None, max_length=64)


class UploadTaskData(BaseModel):
    task_id: int
    task_name: str
    original_file_name: str
    current_version_no: int
    latest_version_id: int
    status: str
    created_at: str


class VersionInfoData(BaseModel):
    version_id: int
    version_no: int
    file_name: str
    file_size: int
    is_current: bool
    source_operation_id: int | None = None
    created_at: str
    download_url: str | None = None


class TaskStatsData(BaseModel):
    operation_count: int
    last_operation_time: str | None = None


class TaskListItemData(BaseModel):
    task_id: int
    task_name: str
    original_file_name: str
    current_version_no: int
    operation_count: int
    last_operation_time: str | None = None
    created_at: str
    updated_at: str


class TaskListData(BaseModel):
    page: int
    page_size: int
    total: int
    items: list[TaskListItemData]


class TaskDetailData(BaseModel):
    task_id: int
    task_name: str
    original_file_name: str
    status: str
    created_by: str | None = None
    created_at: str
    updated_at: str
    current_version_no: int
    latest_version: VersionInfoData
    stats: TaskStatsData
    sheet_names: list[str]


class OperationSummaryData(BaseModel):
    total_count: int
    success_count: int
    not_found_count: int
    duplicate_count: int
    failed_count: int


class OperationListItemData(BaseModel):
    operation_id: int
    operation_no: str
    status: str
    sheet_name: str
    match_column: str
    target_column: str
    total_count: int
    success_count: int
    not_found_count: int
    duplicate_count: int
    failed_count: int
    submitted_by: str | None = None
    submitted_at: str
    finished_at: str | None = None
    result_version_id: int | None = None


class OperationListData(BaseModel):
    page: int
    page_size: int
    total: int
    items: list[OperationListItemData]


class OperationItemResultData(BaseModel):
    id: int | None = None
    match_value: str
    target_value: str | int | float | None = None
    status: str
    row_index: int | None = None
    cell_address: str | None = None
    old_value: str | None = None
    new_value: str | None = None
    message: str | None = None


class OperationExecutionResult(BaseModel):
    summary: OperationSummaryData
    items: list[OperationItemResultData]
    has_successful_updates: bool


class OperationDetailData(BaseModel):
    operation_id: int
    operation_no: str
    task_id: int
    status: str
    base_version_id: int | None = None
    result_version_id: int | None = None
    sheet_name: str
    match_column: str
    target_column: str
    request_payload: dict[str, Any]
    summary: OperationSummaryData
    error_message: str | None = None
    submitted_by: str | None = None
    submitted_at: str
    started_at: str | None = None
    finished_at: str | None = None
    result_version: VersionInfoData | None = None
    item_page: int
    item_page_size: int
    item_total: int
    items: list[OperationItemResultData] = Field(default_factory=list)


class OperationStatusData(BaseModel):
    operation_id: int
    status: str
    submitted_at: str
    started_at: str | None = None
    finished_at: str | None = None
    summary: OperationSummaryData


class VersionListData(BaseModel):
    page: int
    page_size: int
    total: int
    items: list[VersionInfoData]


class DownloadUrlData(BaseModel):
    task_id: int
    version_id: int | None = None
    version_no: int | None = None
    file_name: str
    download_url: str
    expires_in: int = 3600


class DownloadedFile(BaseModel):
    file_name: str
    content: bytes
