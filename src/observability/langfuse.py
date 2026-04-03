from contextlib import contextmanager
from functools import lru_cache
from typing import Any, Iterator

from langfuse import Langfuse

from src.config.settings import settings


def langfuse_enabled() -> bool:
    return bool(
        settings.langfuse_enabled
        and settings.langfuse_public_key
        and settings.langfuse_secret_key
    )


@lru_cache(maxsize=1)
def get_langfuse_client() -> Langfuse | None:
    if not langfuse_enabled():
        return None

    return Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        base_url=settings.langfuse_base_url,
        debug=settings.langfuse_debug,
        flush_at=max(settings.langfuse_flush_at, 1),
        environment=settings.app_env,
        release=settings.app_name,
    )


@contextmanager
def observe(
    *,
    name: str,
    as_type: str = "span",
    input: Any = None,
    output: Any = None,
    metadata: Any = None,
    model: str | None = None,
    model_parameters: dict[str, Any] | None = None,
) -> Iterator[Any]:
    client = get_langfuse_client()
    if client is None:
        yield None
        return

    with client.start_as_current_observation(
        name=name,
        as_type=as_type,
        input=input,
        output=output,
        metadata=metadata,
        model=model,
        model_parameters=model_parameters,
    ) as observation:
        yield observation


def current_trace_info() -> tuple[str | None, str | None]:
    client = get_langfuse_client()
    if client is None:
        return None, None

    trace_id = client.get_current_trace_id()
    if trace_id is None:
        return None, None

    return trace_id, client.get_trace_url(trace_id=trace_id)


def flush_langfuse() -> None:
    client = get_langfuse_client()
    if client is not None:
        client.flush()

