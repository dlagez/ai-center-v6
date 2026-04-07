import subprocess
from dataclasses import dataclass
from pathlib import Path

from src.config.settings import settings


@dataclass(slots=True)
class ExtractedFrame:
    frame_index: int
    timestamp_seconds: int
    frame_path: Path


def _ensure_video_exists(video_path: str) -> Path:
    path = Path(video_path).expanduser()
    if not path.is_file():
        raise ValueError(f"Video file not found: {path}")
    return path


def _resolve_frames_dir(video_path: Path, frames_dir: str | None = None) -> Path:
    if frames_dir:
        resolved = Path(frames_dir).expanduser()
    else:
        resolved = Path(settings.media_frames_dir) / video_path.stem
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def extract_video_frames(
    video_path: str,
    interval_seconds: int,
    frames_dir: str | None = None,
) -> tuple[list[ExtractedFrame], Path]:
    if interval_seconds <= 0:
        raise ValueError("interval_seconds must be greater than 0")

    resolved_video_path = _ensure_video_exists(video_path)
    resolved_frames_dir = _resolve_frames_dir(resolved_video_path, frames_dir)
    output_pattern = resolved_frames_dir / "frame_%06d.jpg"

    command = [
        settings.media_ffmpeg_binary,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(resolved_video_path),
        "-vf",
        f"fps=1/{interval_seconds}",
        "-start_number",
        "0",
        str(output_pattern),
    ]

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise ValueError(
            f"FFmpeg binary not found: {settings.media_ffmpeg_binary}"
        ) from exc

    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        detail = stderr or "Unknown FFmpeg error"
        raise ValueError(f"Frame extraction failed: {detail}")

    frame_paths = sorted(resolved_frames_dir.glob("frame_*.jpg"))
    if not frame_paths:
        raise ValueError("No frames were extracted from the video")

    frames = [
        ExtractedFrame(
            frame_index=index,
            timestamp_seconds=index * interval_seconds,
            frame_path=frame_path,
        )
        for index, frame_path in enumerate(frame_paths)
    ]
    return frames, resolved_frames_dir
