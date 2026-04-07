from typing import Any

from pydantic import BaseModel, Field


class FrameInspectionResult(BaseModel):
    frame_index: int = Field(..., description="Zero-based frame index after extraction.")
    timestamp_seconds: int = Field(..., description="Approximate frame timestamp in seconds.")
    frame_path: str | None = Field(
        default=None,
        description="Local frame path if frames are kept on disk.",
    )
    raw_answer: str = Field(..., description="Raw model output for this frame.")
    parsed_result: dict[str, Any] | None = Field(
        default=None,
        description="Parsed JSON object when the model output is valid JSON.",
    )
    is_match: bool | None = Field(
        default=None,
        description="Boolean match extracted from parsed_result[match_field] when available.",
    )


class VideoInspectionResult(BaseModel):
    video_path: str = Field(..., description="Input video path.")
    interval_seconds: int = Field(..., description="Frame extraction interval in seconds.")
    total_frames: int = Field(..., description="Total extracted frames inspected.")
    match_field: str | None = Field(
        default=None,
        description="JSON boolean field used to determine frame matches.",
    )
    has_match: bool | None = Field(
        default=None,
        description="True if any frame matched, null when match_field was not provided.",
    )
    frames_dir: str | None = Field(
        default=None,
        description="Directory that stores extracted frames when retained.",
    )
    frames: list[FrameInspectionResult] = Field(
        default_factory=list,
        description="Inspection results for each extracted frame.",
    )
    excel_path: str | None = Field(
        default=None,
        description="Generated Excel report path when export is enabled.",
    )
