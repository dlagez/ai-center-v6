from typing import Any

from litellm import completion

from src.config.settings import settings
from src.observability import observe


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
    resolved_temperature = settings.llm_temperature if temperature is None else temperature
    req: dict[str, Any] = {
        "model": model_name,
        "messages": messages,
        "timeout": settings.llm_timeout,
        "temperature": resolved_temperature,
    }

    if max_tokens is not None:
        req["max_tokens"] = max_tokens

    api_base = _resolve_api_base(model_name)
    if api_base:
        req["api_base"] = api_base
    if model_name.startswith("dashscope/") and settings.dashscope_api_key:
        req["api_key"] = settings.dashscope_api_key

    req.update(kwargs)

    with observe(
        name="litellm.chat_completion",
        as_type="generation",
        input=messages,
        metadata={"api_base": api_base},
        model=model_name,
        model_parameters={
            "temperature": resolved_temperature,
            "max_tokens": max_tokens,
            "timeout": settings.llm_timeout,
        },
    ) as observation:
        resp = completion(**req)
        content = resp.choices[0].message.content or ""
        if observation is not None:
            observation.update(output=content)
        return content
