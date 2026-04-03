from typing import Any

from litellm import embedding

from src.config.settings import settings
from src.models.llm import _resolve_api_base


def embed_texts(
    texts: list[str],
    model: str | None = None,
    **kwargs: Any,
) -> list[list[float]]:
    if not texts:
        return []

    model_name = model or settings.embedding_model
    api_base = _resolve_api_base(model_name)
    vectors: list[list[float]] = []
    batch_size = max(settings.embedding_batch_size, 1)

    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        req: dict[str, Any] = {
            "model": model_name,
            "input": batch,
            "timeout": settings.llm_timeout,
        }
        if api_base:
            req["api_base"] = api_base

        req.update(kwargs)
        resp = embedding(**req)
        vectors.extend([list(item.embedding) for item in resp.data])

    return vectors


def embed_query(text: str, model: str | None = None, **kwargs: Any) -> list[float]:
    vectors = embed_texts([text], model=model, **kwargs)
    return vectors[0] if vectors else []
