import base64
import mimetypes
from pathlib import Path
from typing import Any

from litellm import completion

from src.config.settings import settings
from src.observability import observe


def _normalize_model_name(model_name: str) -> str:
    if "/" in model_name:
        return model_name
    if model_name.startswith(("qwen-", "qvq-")):
        return f"dashscope/{model_name}"
    return model_name


def _resolve_api_base(model_name: str) -> str | None:
    if settings.llm_api_base:
        return settings.llm_api_base
    if model_name.startswith("dashscope/") and settings.dashscope_api_base:
        return settings.dashscope_api_base
    return None


def _image_path_to_data_url(image_path: str) -> str:
    path = Path(image_path).expanduser()
    if not path.is_file():
        raise ValueError(f"Image file not found: {path}")

    mime_type, _ = mimetypes.guess_type(path.name)
    if not mime_type or not mime_type.startswith("image/"):
        raise ValueError(f"Unsupported image file type: {path.name}")

    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _build_vision_content(
    prompt: str,
    image_url: str | None = None,
    image_path: str | None = None,
) -> list[dict[str, Any]]:
    if not prompt.strip():
        raise ValueError("Prompt must not be empty")
    if bool(image_url) == bool(image_path):
        raise ValueError("Provide exactly one of image_url or image_path")

    resolved_image_url = image_url or _image_path_to_data_url(image_path or "")
    return [
        {"type": "text", "text": prompt},
        {"type": "image_url", "image_url": {"url": resolved_image_url}},
    ]


def chat_completion(
    messages: list[dict[str, Any]],
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    **kwargs: Any,
) -> str:
    model_name = _normalize_model_name(model or settings.llm_default_model)
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


def vision_completion(
    prompt: str,
    image_url: str | None = None,
    image_path: str | None = None,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    **kwargs: Any,
) -> str:
    messages = [
        {
            "role": "user",
            "content": _build_vision_content(
                prompt=prompt,
                image_url=image_url,
                image_path=image_path,
            ),
        }
    ]
    return chat_completion(
        messages=messages,
        model=model or settings.llm_vision_model,
        temperature=temperature,
        max_tokens=max_tokens,
        **kwargs,
    )
