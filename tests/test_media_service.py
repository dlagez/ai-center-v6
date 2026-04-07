import json

from src.media.prompts import DEFAULT_PERSONNEL_INSPECTION_PROMPT
from src.media.service import VideoInspectionService
from src.media.video import ExtractedFrame


def _work_paths(tmp_path):
    work_dir = tmp_path / "job"
    frames_dir = work_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    return {
        "work_dir": work_dir,
        "frames_dir": frames_dir,
        "excel_path": work_dir / "inspection.xlsx",
        "checkpoint_path": work_dir / "checkpoint.json",
        "request_path": work_dir / "request.json",
    }


def test_video_inspection_service_aggregates_match_field(monkeypatch, tmp_path) -> None:
    work_paths = _work_paths(tmp_path)
    frame_a = work_paths["frames_dir"] / "frame_000000.jpg"
    frame_b = work_paths["frames_dir"] / "frame_000001.jpg"
    frame_a.write_bytes(b"a")
    frame_b.write_bytes(b"b")

    monkeypatch.setattr("src.media.service.build_work_paths", lambda _: work_paths)
    monkeypatch.setattr(
        "src.media.service.extract_video_frames",
        lambda **kwargs: (
            [
                ExtractedFrame(frame_index=0, timestamp_seconds=0, frame_path=frame_a),
                ExtractedFrame(frame_index=1, timestamp_seconds=20, frame_path=frame_b),
            ],
            work_paths["frames_dir"],
        ),
    )

    def fake_inspect_image(**kwargs):
        if kwargs["image_path"] == str(frame_a):
            return '{"has_reflective_vest": false}', {"has_reflective_vest": False}
        return '{"has_reflective_vest": true}', {"has_reflective_vest": True}

    monkeypatch.setattr("src.media.service.inspect_image", fake_inspect_image)
    monkeypatch.setattr(
        "src.media.service.ExcelReportWriter",
        type(
            "FakeExcelReportWriter",
            (),
            {
                "__init__": lambda self, **kwargs: setattr(self, "output_path", kwargs["output_path"]),
                "append_frame": lambda self, frame: None,
            },
        ),
    )

    service = VideoInspectionService()
    result = service.inspect_video(
        video_path="demo.mp4",
        prompt="检测是否有穿反光衣的人，只返回 JSON",
        interval_seconds=20,
        match_field="has_reflective_vest",
    )

    assert result.total_frames == 2
    assert result.has_match is True
    assert result.frames_dir == str(work_paths["frames_dir"])
    assert result.work_dir == str(work_paths["work_dir"])
    assert result.checkpoint_path == str(work_paths["checkpoint_path"])
    assert result.excel_path == str(work_paths["excel_path"])
    assert [frame.is_match for frame in result.frames] == [False, True]


def test_video_inspection_service_removes_frames_when_not_kept(monkeypatch, tmp_path) -> None:
    work_paths = _work_paths(tmp_path)
    frame_path = work_paths["frames_dir"] / "frame_000000.jpg"
    frame_path.write_bytes(b"a")

    monkeypatch.setattr("src.media.service.build_work_paths", lambda _: work_paths)
    monkeypatch.setattr(
        "src.media.service.extract_video_frames",
        lambda **kwargs: (
            [ExtractedFrame(frame_index=0, timestamp_seconds=0, frame_path=frame_path)],
            work_paths["frames_dir"],
        ),
    )
    monkeypatch.setattr(
        "src.media.service.inspect_image",
        lambda **kwargs: ('{"ok": true}', {"ok": True}),
    )
    monkeypatch.setattr(
        "src.media.service.ExcelReportWriter",
        type(
            "FakeExcelReportWriter",
            (),
            {
                "__init__": lambda self, **kwargs: setattr(self, "output_path", kwargs["output_path"]),
                "append_frame": lambda self, frame: None,
            },
        ),
    )

    service = VideoInspectionService()
    result = service.inspect_video(
        video_path="demo.mp4",
        prompt="返回 JSON",
        keep_frames=False,
    )

    assert result.frames_dir is None
    assert result.frames[0].frame_path is None
    assert not work_paths["frames_dir"].exists()


def test_video_inspection_service_exports_excel_and_checkpoint_per_frame(monkeypatch, tmp_path) -> None:
    work_paths = _work_paths(tmp_path)
    frame_a = work_paths["frames_dir"] / "frame_000000.jpg"
    frame_b = work_paths["frames_dir"] / "frame_000001.jpg"
    frame_a.write_bytes(b"a")
    frame_b.write_bytes(b"b")

    monkeypatch.setattr("src.media.service.build_work_paths", lambda _: work_paths)
    monkeypatch.setattr(
        "src.media.service.extract_video_frames",
        lambda **kwargs: (
            [
                ExtractedFrame(frame_index=0, timestamp_seconds=0, frame_path=frame_a),
                ExtractedFrame(frame_index=1, timestamp_seconds=60, frame_path=frame_b),
            ],
            work_paths["frames_dir"],
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

    appended: list[int] = []

    class FakeExcelReportWriter:
        def __init__(self, *, video_path, interval_seconds, output_path):
            self.output_path = output_path

        def append_frame(self, frame):
            appended.append(frame.frame_index)

    monkeypatch.setattr("src.media.service.ExcelReportWriter", FakeExcelReportWriter)

    service = VideoInspectionService()
    result = service.inspect_video(
        video_path="demo.mp4",
        prompt="返回 JSON",
    )

    checkpoint = json.loads(work_paths["checkpoint_path"].read_text(encoding="utf-8"))
    assert result.excel_path == str(work_paths["excel_path"])
    assert appended == [0, 1]
    assert len(checkpoint["completed_frames"]) == 2


def test_video_inspection_service_resumes_from_checkpoint(monkeypatch, tmp_path) -> None:
    work_paths = _work_paths(tmp_path)
    frame_a = work_paths["frames_dir"] / "frame_000000.jpg"
    frame_b = work_paths["frames_dir"] / "frame_000001.jpg"
    frame_a.write_bytes(b"a")
    frame_b.write_bytes(b"b")

    checkpoint_payload = {
        "video_path": "demo.mp4",
        "interval_seconds": 60,
        "work_dir": str(work_paths["work_dir"]),
        "frames_dir": str(work_paths["frames_dir"]),
        "excel_path": str(work_paths["excel_path"]),
        "match_field": None,
        "completed_frames": [
            {
                "frame_index": 0,
                "timestamp_seconds": 0,
                "frame_path": str(frame_a),
                "raw_answer": '{"是否为管理人员":"否"}',
                "parsed_result": {"是否为管理人员": "否"},
                "is_match": None,
            }
        ],
    }
    work_paths["checkpoint_path"].write_text(
        json.dumps(checkpoint_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    monkeypatch.setattr("src.media.service.build_work_paths", lambda _: work_paths)
    monkeypatch.setattr(
        "src.media.service.extract_video_frames",
        lambda **kwargs: (
            [
                ExtractedFrame(frame_index=0, timestamp_seconds=0, frame_path=frame_a),
                ExtractedFrame(frame_index=1, timestamp_seconds=60, frame_path=frame_b),
            ],
            work_paths["frames_dir"],
        ),
    )

    inspected_paths: list[str] = []

    def fake_inspect_image(**kwargs):
        inspected_paths.append(kwargs["image_path"])
        return '{"是否为管理人员":"是"}', {"是否为管理人员": "是"}

    monkeypatch.setattr("src.media.service.inspect_image", fake_inspect_image)

    appended: list[int] = []

    class FakeExcelReportWriter:
        def __init__(self, *, video_path, interval_seconds, output_path):
            self.output_path = output_path

        def append_frame(self, frame):
            appended.append(frame.frame_index)

    monkeypatch.setattr("src.media.service.ExcelReportWriter", FakeExcelReportWriter)

    service = VideoInspectionService()
    result = service.inspect_video(video_path="demo.mp4", prompt="返回 JSON")

    assert inspected_paths == [str(frame_b)]
    assert appended == [1]
    assert [frame.frame_index for frame in result.frames] == [0, 1]


def test_video_inspection_service_uses_default_prompt_when_missing(monkeypatch, tmp_path) -> None:
    work_paths = _work_paths(tmp_path)
    frame_path = work_paths["frames_dir"] / "frame_000000.jpg"
    frame_path.write_bytes(b"a")
    captured: dict[str, str] = {}

    monkeypatch.setattr("src.media.service.build_work_paths", lambda _: work_paths)
    monkeypatch.setattr(
        "src.media.service.extract_video_frames",
        lambda **kwargs: (
            [ExtractedFrame(frame_index=0, timestamp_seconds=0, frame_path=frame_path)],
            work_paths["frames_dir"],
        ),
    )

    def fake_inspect_image(**kwargs):
        captured["prompt"] = kwargs["prompt"]
        return '{"是否为管理人员":"否"}', {"是否为管理人员": "否"}

    monkeypatch.setattr("src.media.service.inspect_image", fake_inspect_image)
    monkeypatch.setattr(
        "src.media.service.ExcelReportWriter",
        type(
            "FakeExcelReportWriter",
            (),
            {
                "__init__": lambda self, **kwargs: setattr(self, "output_path", kwargs["output_path"]),
                "append_frame": lambda self, frame: None,
            },
        ),
    )

    service = VideoInspectionService()
    service.inspect_video(video_path="demo.mp4", prompt=None)

    assert captured["prompt"] == DEFAULT_PERSONNEL_INSPECTION_PROMPT
