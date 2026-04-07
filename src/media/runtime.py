import hashlib
import json
import re
from pathlib import Path
from typing import Any

from src.config.settings import settings
from src.media.schemas import FrameInspectionResult


def _sanitize_name(name: str) -> str:
    sanitized = re.sub(r'[<>:"/\\|?*]+', "_", name).strip(" .")
    return sanitized or "video"


def build_work_dir(video_path: str) -> Path:
    resolved_video = Path(video_path).expanduser().resolve(strict=False)
    digest = hashlib.sha1(str(resolved_video).encode("utf-8")).hexdigest()[:8]
    dir_name = f"{_sanitize_name(resolved_video.stem)}_{digest}"
    work_dir = Path(settings.media_output_dir).expanduser() / dir_name
    work_dir.mkdir(parents=True, exist_ok=True)
    return work_dir


def build_work_paths(video_path: str) -> dict[str, Path]:
    work_dir = build_work_dir(video_path)
    frames_dir = work_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    return {
        "work_dir": work_dir,
        "frames_dir": frames_dir,
        "excel_path": work_dir / "inspection.xlsx",
        "checkpoint_path": work_dir / "checkpoint.json",
        "request_path": work_dir / "request.json",
    }


def save_request_metadata(request_path: Path, payload: dict[str, Any]) -> None:
    request_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_checkpoint(checkpoint_path: Path) -> dict[str, Any]:
    if not checkpoint_path.is_file():
        return {"completed_frames": []}
    return json.loads(checkpoint_path.read_text(encoding="utf-8"))


def save_checkpoint(
    checkpoint_path: Path,
    *,
    video_path: str,
    interval_seconds: int,
    work_dir: str,
    frames_dir: str,
    excel_path: str | None,
    match_field: str | None,
    frames: list[FrameInspectionResult],
) -> None:
    payload = {
        "video_path": video_path,
        "interval_seconds": interval_seconds,
        "work_dir": work_dir,
        "frames_dir": frames_dir,
        "excel_path": excel_path,
        "match_field": match_field,
        "completed_frames": [frame.model_dump() for frame in frames],
    }
    checkpoint_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def restore_frame_results(checkpoint_data: dict[str, Any]) -> list[FrameInspectionResult]:
    frames = checkpoint_data.get("completed_frames", [])
    return [FrameInspectionResult.model_validate(frame) for frame in frames]
