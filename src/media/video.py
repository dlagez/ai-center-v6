import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from src.config.settings import settings


@dataclass(slots=True)
class ExtractedFrame:
    frame_index: int
    timestamp_seconds: int
    frame_path: Path


def _ffmpeg_candidates() -> list[Path]:
    candidates: list[Path] = []

    configured = settings.media_ffmpeg_binary.strip()
    if configured:
        candidates.append(Path(configured).expanduser())

    env_ffmpeg = os.getenv("FFMPEG_BINARY")
    if env_ffmpeg:
        candidates.append(Path(env_ffmpeg).expanduser())

    local_appdata = Path(os.getenv("LOCALAPPDATA", ""))
    user_profile = Path(os.getenv("USERPROFILE", ""))

    common_paths = [
        user_profile / ".stacher" / "ffmpeg.exe",
        local_appdata / "Microsoft" / "WinGet" / "Packages",
        Path("C:/ffmpeg/bin/ffmpeg.exe"),
        Path("C:/Program Files/ffmpeg/bin/ffmpeg.exe"),
        Path("C:/Program Files (x86)/ffmpeg/bin/ffmpeg.exe"),
    ]
    candidates.extend(common_paths)
    return candidates


def _resolve_ffmpeg_binary() -> str:
    configured = settings.media_ffmpeg_binary.strip()
    if configured:
        resolved = shutil.which(configured)
        if resolved:
            return resolved

        configured_path = Path(configured).expanduser()
        if configured_path.is_file():
            return str(configured_path)

    env_ffmpeg = os.getenv("FFMPEG_BINARY")
    if env_ffmpeg:
        resolved_env = shutil.which(env_ffmpeg)
        if resolved_env:
            return resolved_env

        env_path = Path(env_ffmpeg).expanduser()
        if env_path.is_file():
            return str(env_path)

    stacher_path = Path(os.getenv("USERPROFILE", "")) / ".stacher" / "ffmpeg.exe"
    if stacher_path.is_file():
        return str(stacher_path)

    local_appdata = Path(os.getenv("LOCALAPPDATA", ""))
    if local_appdata:
        winget_match = next(local_appdata.glob("Microsoft/WinGet/Packages/**/ffmpeg.exe"), None)
        if winget_match and winget_match.is_file():
            return str(winget_match)

    for path in [
        Path("C:/ffmpeg/bin/ffmpeg.exe"),
        Path("C:/Program Files/ffmpeg/bin/ffmpeg.exe"),
        Path("C:/Program Files (x86)/ffmpeg/bin/ffmpeg.exe"),
    ]:
        if path.is_file():
            return str(path)

    raise ValueError(
        "FFmpeg binary not found. "
        "Set MEDIA_FFMPEG_BINARY in .env, or install ffmpeg so it is available in PATH."
    )


def _ensure_video_exists(video_path: str) -> Path:
    path = Path(video_path).expanduser()
    if not path.is_file():
        raise ValueError(f"Video file not found: {path}")
    return path


def _resolve_frames_dir(video_path: Path, frames_dir: str | None = None) -> Path:
    if frames_dir:
        resolved = Path(frames_dir).expanduser()
    else:
        resolved = Path(settings.media_output_dir).expanduser() / "frames" / video_path.stem
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
    ffmpeg_binary = _resolve_ffmpeg_binary()

    command = [
        ffmpeg_binary,
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
            f"FFmpeg binary not found: {ffmpeg_binary}"
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
