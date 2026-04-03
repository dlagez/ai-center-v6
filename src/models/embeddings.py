from typing import Any

from litellm import embedding

from src.config.settings import settings


def _extract_embedding_vector(item: Any) -> list[float]:
    if isinstance(item, dict):
        return list(item["embedding"])
    return list(item.embedding)


def embed_texts(
    texts: list[str],
    model: str | None = None,
    **kwargs: Any,
) -> list[list[float]]:
    if not texts:
        return []

    model_name = model or settings.embedding_model
    vectors: list[list[float]] = []
    batch_size = max(settings.embedding_batch_size, 1)

    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        req: dict[str, Any] = {
            "model": model_name,
            "input": batch,
            "timeout": settings.llm_timeout,
            "encoding_format": "float",
        }
        if settings.dashscope_api_base:
            req["api_base"] = settings.dashscope_api_base
        if settings.dashscope_api_key:
            req["api_key"] = settings.dashscope_api_key

        req.update(kwargs)
        resp = embedding(**req)
        vectors.extend([_extract_embedding_vector(item) for item in resp.data])

    return vectors


def embed_query(text: str, model: str | None = None, **kwargs: Any) -> list[float]:
    vectors = embed_texts([text], model=model, **kwargs)
    return vectors[0] if vectors else []
