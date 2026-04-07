from fastapi.testclient import TestClient

from src.api.app import app

client = TestClient(app)


def test_vision_chat_endpoint_returns_answer(monkeypatch) -> None:
    def fake_vision_completion(**kwargs):
        assert kwargs["prompt"] == "图里有什么？"
        assert kwargs["image_url"] == "https://example.com/cat.jpg"
        assert kwargs["model"] == "qwen-vl-max-latest"
        assert kwargs["max_tokens"] == 256
        return "这是一只猫。"

    monkeypatch.setattr("src.api.routes.vision_completion", fake_vision_completion)

    response = client.post(
        "/models/vision/chat",
        json={
            "prompt": "图里有什么？",
            "image_url": "https://example.com/cat.jpg",
            "model": "qwen-vl-max-latest",
            "max_tokens": 256,
        },
    )

    assert response.status_code == 200
    assert response.json() == {"answer": "这是一只猫。"}


def test_vision_chat_endpoint_maps_validation_errors(monkeypatch) -> None:
    def fake_vision_completion(**kwargs):
        raise ValueError("Provide exactly one of image_url or image_path")

    monkeypatch.setattr("src.api.routes.vision_completion", fake_vision_completion)

    response = client.post(
        "/models/vision/chat",
        json={"prompt": "图里有什么？", "image_url": "https://example.com/cat.jpg"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Provide exactly one of image_url or image_path"
