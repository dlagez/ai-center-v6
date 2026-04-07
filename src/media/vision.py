import json
from typing import Any

from src.models.llm import vision_completion


def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped

    lines = stripped.splitlines()
    if len(lines) >= 3 and lines[0].startswith("```") and lines[-1] == "```":
        return "\n".join(lines[1:-1]).strip()
    return stripped


def try_parse_json_object(text: str) -> dict[str, Any] | None:
    candidate = _strip_code_fence(text)
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def inspect_image(
    *,
    prompt: str,
    image_path: str,
    model: str | None = None,
    max_tokens: int | None = None,
) -> tuple[str, dict[str, Any] | None]:
    raw_answer = vision_completion(
        prompt=prompt,
        image_path=image_path,
        model=model,
        max_tokens=max_tokens,
    )
    return raw_answer, try_parse_json_object(raw_answer)
