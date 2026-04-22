from datetime import datetime

from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    source: str = Field(..., description="File or directory path to ingest.")


class SearchRequest(BaseModel):
    query: str = Field(..., description="User query for vector search.")
    limit: int = Field(default=5, ge=1, le=20, description="Maximum number of chunks to return.")


class AgenticRagRequest(BaseModel):
    question: str = Field(..., description="User question for agentic RAG.")
    limit: int = Field(default=5, ge=1, le=20, description="Maximum number of retrieved chunks.")


class SqlAgentRequest(BaseModel):
    question: str = Field(..., description="User question for the SQL agent.")
    dialect: str | None = Field(default=None, description="Database dialect: sqlite or mysql.")
    db_path: str | None = Field(default=None, description="SQLite database file path.")
    max_rows: int = Field(default=20, ge=1, le=100, description="Maximum number of rows to read.")


class SystemConfigCreateRequest(BaseModel):
    key: str = Field(..., min_length=1, max_length=100, description="Configuration key.")
    value: str = Field(..., description="Configuration value.")


class SystemConfigUpdateRequest(BaseModel):
    value: str = Field(..., description="Configuration value.")


class SystemConfigResponse(BaseModel):
    id: int
    key: str
    value: str
    created_at: datetime
    updated_at: datetime


class FileUploadResponse(BaseModel):
    file_id: str
    file_name: str
    content_type: str
    file_size: int
    biz_type: str
    folder_path: str
    object_name: str
    url: str
    etag: str


class PdfPreviewFileResponse(BaseModel):
    file_id: str
    file_name: str
    stored_name: str
    object_name: str
    bucket_name: str
    biz_type: str
    date_folder: str
    folder_path: str
    content_type: str
    file_size: int
    file_ext: str | None
    created_at: datetime


class VisionChatRequest(BaseModel):
    prompt: str = Field(..., description="User prompt for vision understanding.")
    image_url: str | None = Field(default=None, description="Public image URL or data URL.")
    image_path: str | None = Field(default=None, description="Local image file path on the server.")
    model: str | None = Field(
        default=None,
        description="Vision model name, e.g. dashscope/qwen-vl-plus-latest.",
    )
    max_tokens: int | None = Field(default=None, ge=1, le=8192, description="Maximum output tokens.")


class VideoInspectionRequest(BaseModel):
    video_path: str = Field(..., description="Local video file path on the server.")
    prompt: str | None = Field(
        default=None,
        description="Optional prompt sent for each extracted frame. Uses the built-in inspection prompt when omitted.",
    )
    interval_seconds: int = Field(
        default=60,
        ge=1,
        le=3600,
        description="Extract one frame every N seconds.",
    )
    model: str | None = Field(
        default=None,
        description="Vision model name, e.g. dashscope/qwen-vl-plus-latest.",
    )
    max_tokens: int | None = Field(default=None, ge=1, le=8192, description="Maximum output tokens.")
    match_field: str | None = Field(
        default=None,
        description="Optional JSON boolean field name used to aggregate matches.",
    )
    frames_dir: str | None = Field(
        default=None,
        description="Optional directory to store extracted frames.",
    )
    keep_frames: bool = Field(
        default=True,
        description="Whether to keep extracted frames on disk after inspection.",
    )
    export_excel_path: str | None = Field(
        default=None,
        description="Optional output path for the Excel report.",
    )
