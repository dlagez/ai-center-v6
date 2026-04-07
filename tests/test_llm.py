from src.models import llm


class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeChoice:
    def __init__(self, content: str) -> None:
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content: str) -> None:
        self.choices = [_FakeChoice(content)]


def test_chat_completion_uses_dashscope_api_base(monkeypatch) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(llm.settings, "llm_api_base", None)
    monkeypatch.setattr(
        llm.settings,
        "dashscope_api_base",
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
    )

    def fake_completion(**kwargs):
        captured.update(kwargs)
        return _FakeResponse("ok")

    monkeypatch.setattr(llm, "completion", fake_completion)

    result = llm.chat_completion(
        model="dashscope/qwen-plus",
        messages=[{"role": "user", "content": "hello"}],
    )

    assert result == "ok"
    assert captured["api_base"] == "https://dashscope.aliyuncs.com/compatible-mode/v1"


def test_vision_completion_builds_multimodal_request(monkeypatch) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(llm.settings, "llm_vision_model", "dashscope/qwen-vl-plus-latest")

    def fake_chat_completion(**kwargs):
        captured.update(kwargs)
        return "image ok"

    monkeypatch.setattr(llm, "chat_completion", fake_chat_completion)

    result = llm.vision_completion(
        prompt="Describe the image",
        image_url="https://example.com/demo.png",
    )

    assert result == "image ok"
    assert captured["model"] == "dashscope/qwen-vl-plus-latest"
    assert captured["messages"] == [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Describe the image"},
                {"type": "image_url", "image_url": {"url": "https://example.com/demo.png"}},
            ],
        }
    ]
