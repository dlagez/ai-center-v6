from pathlib import Path

import pytest

from src.media import video


def test_resolve_ffmpeg_binary_from_direct_file(monkeypatch, tmp_path) -> None:
    ffmpeg_path = tmp_path / "ffmpeg.exe"
    ffmpeg_path.write_text("bin", encoding="utf-8")

    monkeypatch.setattr(video.settings, "media_ffmpeg_binary", str(ffmpeg_path))
    monkeypatch.setattr(video.shutil, "which", lambda _: None)
    monkeypatch.setenv("FFMPEG_BINARY", "")
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    assert video._resolve_ffmpeg_binary() == str(ffmpeg_path)


def test_resolve_ffmpeg_binary_from_stacher(monkeypatch, tmp_path) -> None:
    stacher_dir = tmp_path / ".stacher"
    stacher_dir.mkdir()
    ffmpeg_path = stacher_dir / "ffmpeg.exe"
    ffmpeg_path.write_text("bin", encoding="utf-8")

    monkeypatch.setattr(video.settings, "media_ffmpeg_binary", "ffmpeg")
    monkeypatch.setattr(video.shutil, "which", lambda _: None)
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.delenv("FFMPEG_BINARY", raising=False)

    assert video._resolve_ffmpeg_binary() == str(ffmpeg_path)


def test_resolve_ffmpeg_binary_raises_clear_error(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(video.settings, "media_ffmpeg_binary", "ffmpeg")
    monkeypatch.setattr(video.shutil, "which", lambda _: None)
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.delenv("FFMPEG_BINARY", raising=False)

    with pytest.raises(ValueError, match="FFmpeg binary not found"):
        video._resolve_ffmpeg_binary()
