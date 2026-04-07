from fastapi.testclient import TestClient

from src.api.app import app
from src.media.schemas import VideoInspectionResult

client = TestClient(app)


def test_video_inspect_endpoint_returns_result(monkeypatch) -> None:
    def fake_inspect_video(self, **kwargs):
        assert kwargs["video_path"] == "D:/videos/demo.mp4"
        assert kwargs["prompt"] == "检测是否有反光衣，只返回 JSON"
        assert kwargs["interval_seconds"] == 20
        assert kwargs["match_field"] == "has_reflective_vest"
        return VideoInspectionResult.model_validate(
            {
                "video_path": kwargs["video_path"],
                "interval_seconds": 20,
                "total_frames": 1,
                "match_field": "has_reflective_vest",
                "has_match": True,
                "frames_dir": "D:/frames/demo",
                "frames": [
                    {
                        "frame_index": 0,
                        "timestamp_seconds": 0,
                        "frame_path": "D:/frames/demo/frame_000000.jpg",
                        "raw_answer": '{"has_reflective_vest": true}',
                        "parsed_result": {"has_reflective_vest": True},
                        "is_match": True,
                    }
                ],
            }
        )

    monkeypatch.setattr("src.api.routes.VideoInspectionService.inspect_video", fake_inspect_video)

    response = client.post(
        "/media/video/inspect",
        json={
            "video_path": "D:/videos/demo.mp4",
            "prompt": "检测是否有反光衣，只返回 JSON",
            "interval_seconds": 20,
            "match_field": "has_reflective_vest",
        },
    )

    assert response.status_code == 200
    assert response.json()["has_match"] is True
    assert response.json()["frames"][0]["is_match"] is True


def test_video_inspect_endpoint_maps_validation_errors(monkeypatch) -> None:
    def fake_inspect_video(self, **kwargs):
        raise ValueError("Video file not found: D:/videos/missing.mp4")

    monkeypatch.setattr("src.api.routes.VideoInspectionService.inspect_video", fake_inspect_video)

    response = client.post(
        "/media/video/inspect",
        json={
            "video_path": "D:/videos/missing.mp4",
            "prompt": "检测是否有反光衣，只返回 JSON",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Video file not found: D:/videos/missing.mp4"
