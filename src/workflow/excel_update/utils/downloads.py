from __future__ import annotations

import base64
import json


def encode_download_token(*, object_key: str, file_name: str) -> str:
    payload = json.dumps(
        {
            "object_key": object_key,
            "file_name": file_name,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def decode_download_token(token: str) -> dict[str, str]:
    padding = "=" * (-len(token) % 4)
    payload = base64.urlsafe_b64decode(token + padding).decode("utf-8")
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError("invalid download token")
    object_key = str(data.get("object_key") or "").strip()
    file_name = str(data.get("file_name") or "").strip()
    if not object_key or not file_name:
        raise ValueError("invalid download token")
    return {"object_key": object_key, "file_name": file_name}
