from typing import Any

from litellm import completion

from src.config.settings import settings


def _resolve_api_base(model_name: str) -> str | None:
    if settings.llm_api_base:
        return settings.llm_api_base
    if model_name.startswith("dashscope/") and settings.dashscope_api_base:
        return settings.dashscope_api_base
    return None


def chat_completion(
    messages: list[dict[str, Any]],
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    **kwargs: Any,
) -> str:
    model_name = model or settings.llm_default_model
    req: dict[str, Any] = {
        "model": model_name,
        "messages": messages,
        "timeout": settings.llm_timeout,
        "temperature": settings.llm_temperature if temperature is None else temperature,
    }

    if max_tokens is not None:
        req["max_tokens"] = max_tokens

    api_base = _resolve_api_base(model_name)
    if api_base:
        req["api_base"] = api_base
    if model_name.startswith("dashscope/") and settings.dashscope_api_key:
        req["api_key"] = settings.dashscope_api_key

    req.update(kwargs)

    resp = completion(**req)
    content = resp.choices[0].message.content
    return content if content is not None else ""
