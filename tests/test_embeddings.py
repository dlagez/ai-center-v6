from src.models import embeddings


class _FakeEmbeddingItem:
    def __init__(self, values):
        self.embedding = values


class _FakeEmbeddingResponse:
    def __init__(self, vectors):
        self.data = [_FakeEmbeddingItem(vector) for vector in vectors]


def test_embed_texts_uses_dashscope_api_base(monkeypatch) -> None:
    captured = {}

    monkeypatch.setattr(embeddings.settings, "dashscope_api_key", "secret")
    monkeypatch.setattr(
        embeddings.settings,
        "dashscope_api_base",
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
    )

    def fake_embedding(**kwargs):
        captured.update(kwargs)
        return _FakeEmbeddingResponse([[0.1, 0.2]])

    monkeypatch.setattr(embeddings, "embedding", fake_embedding)

    vectors = embeddings.embed_texts(["hello"], model="openai/text-embedding-v3")

    assert vectors == [[0.1, 0.2]]
    assert captured["model"] == "openai/text-embedding-v3"
    assert captured["api_base"] == "https://dashscope.aliyuncs.com/compatible-mode/v1"
    assert captured["encoding_format"] == "float"
    assert captured["api_key"] == "secret"
