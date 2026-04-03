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
