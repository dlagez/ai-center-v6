from typing import Any

from litellm import completion

from src.config.settings import settings


def chat_completion(
    messages: list[dict[str, Any]],
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    **kwargs: Any,
) -> str:
    req: dict[str, Any] = {
        "model": model or settings.llm_default_model,
        "messages": messages,
        "timeout": settings.llm_timeout,
        "temperature": settings.llm_temperature if temperature is None else temperature,
    }

    if max_tokens is not None:
        req["max_tokens"] = max_tokens

    if settings.llm_api_base:
        req["api_base"] = settings.llm_api_base

    req.update(kwargs)

    resp = completion(**req)
    content = resp.choices[0].message.content
    return content if content is not None else ""
