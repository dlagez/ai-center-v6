from pathlib import Path

from src.media.prompts import DEFAULT_PERSONNEL_INSPECTION_PROMPT
from src.media.service import VideoInspectionService
from src.media.video import ExtractedFrame


def test_video_inspection_service_aggregates_match_field(monkeypatch, tmp_path) -> None:
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir()
    frame_a = frames_dir / "frame_000000.jpg"
    frame_b = frames_dir / "frame_000001.jpg"
    frame_a.write_bytes(b"a")
    frame_b.write_bytes(b"b")

    monkeypatch.setattr(
        "src.media.service.extract_video_frames",
        lambda **kwargs: (
            [
                ExtractedFrame(frame_index=0, timestamp_seconds=0, frame_path=frame_a),
                ExtractedFrame(frame_index=1, timestamp_seconds=20, frame_path=frame_b),
            ],
            frames_dir,
        ),
    )

    def fake_inspect_image(**kwargs):
        if kwargs["image_path"] == str(frame_a):
            return '{"has_reflective_vest": false}', {"has_reflective_vest": False}
        return '{"has_reflective_vest": true}', {"has_reflective_vest": True}

    monkeypatch.setattr("src.media.service.inspect_image", fake_inspect_image)

    service = VideoInspectionService()
    result = service.inspect_video(
        video_path="demo.mp4",
        prompt="检测是否有穿反光衣的人，只返回 JSON",
        interval_seconds=20,
        match_field="has_reflective_vest",
    )

    assert result.total_frames == 2
    assert result.has_match is True
    assert result.frames_dir == str(frames_dir)
    assert [frame.is_match for frame in result.frames] == [False, True]


def test_video_inspection_service_removes_frames_when_not_kept(monkeypatch, tmp_path) -> None:
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir()
    frame_path = frames_dir / "frame_000000.jpg"
    frame_path.write_bytes(b"a")

    monkeypatch.setattr(
        "src.media.service.extract_video_frames",
        lambda **kwargs: (
            [ExtractedFrame(frame_index=0, timestamp_seconds=0, frame_path=frame_path)],
            frames_dir,
        ),
    )
    monkeypatch.setattr(
        "src.media.service.inspect_image",
        lambda **kwargs: ('{"ok": true}', {"ok": True}),
    )

    service = VideoInspectionService()
    result = service.inspect_video(
        video_path="demo.mp4",
        prompt="返回 JSON",
        keep_frames=False,
    )

    assert result.frames_dir is None
    assert result.frames[0].frame_path is None
    assert not frames_dir.exists()


def test_video_inspection_service_exports_excel(monkeypatch, tmp_path) -> None:
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir()
    frame_path = frames_dir / "frame_000000.jpg"
    frame_path.write_bytes(b"a")
    export_path = tmp_path / "report.xlsx"

    monkeypatch.setattr(
        "src.media.service.extract_video_frames",
        lambda **kwargs: (
            [ExtractedFrame(frame_index=0, timestamp_seconds=0, frame_path=frame_path)],
            frames_dir,
        ),
    )
    monkeypatch.setattr(
        "src.media.service.inspect_image",
        lambda **kwargs: (
            '{"安全帽颜色":"红色","反光衣颜色":"黄绿色","爆闪灯颜色":"无","是否为管理人员":"否","判定依据":"示例"}',
            {
                "安全帽颜色": "红色",
                "反光衣颜色": "黄绿色",
                "爆闪灯颜色": "无",
                "是否为管理人员": "否",
                "判定依据": "示例",
            },
        ),
    )
    monkeypatch.setattr(
        "src.media.service.export_video_inspection_report",
        lambda result, output_path: output_path,
    )

    service = VideoInspectionService()
    result = service.inspect_video(
        video_path="demo.mp4",
        prompt="返回 JSON",
        export_excel_path=str(export_path),
    )

    assert result.excel_path == str(export_path)


def test_video_inspection_service_uses_default_prompt_when_missing(monkeypatch, tmp_path) -> None:
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir()
    frame_path = frames_dir / "frame_000000.jpg"
    frame_path.write_bytes(b"a")
    captured: dict[str, str] = {}

    monkeypatch.setattr(
        "src.media.service.extract_video_frames",
        lambda **kwargs: (
            [ExtractedFrame(frame_index=0, timestamp_seconds=0, frame_path=frame_path)],
            frames_dir,
        ),
    )

    def fake_inspect_image(**kwargs):
        captured["prompt"] = kwargs["prompt"]
        return '{"是否为管理人员":"否"}', {"是否为管理人员": "否"}

    monkeypatch.setattr("src.media.service.inspect_image", fake_inspect_image)

    service = VideoInspectionService()
    service.inspect_video(
        video_path="demo.mp4",
        prompt=None,
    )

    assert captured["prompt"] == DEFAULT_PERSONNEL_INSPECTION_PROMPT
