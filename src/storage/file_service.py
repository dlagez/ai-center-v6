import mimetypes
import re
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from src.config.settings import settings
from src.storage.minio_client import get_minio_client

DEFAULT_PRESIGNED_URL_EXPIRE = timedelta(hours=1)


class FileService:
    def __init__(self, bucket_name: str | None = None):
        self.client = get_minio_client()
        self.bucket_name = bucket_name or settings.minio_bucket

    def upload_file(self, file, object_name: str | None = None) -> dict[str, str]:
        original_name = getattr(file, "filename", None)
        resolved_object_name = self._normalize_object_name(
            object_name or self.build_object_name(original_name)
        )
        stream, length = self._prepare_stream(file)
        content_type = (
            getattr(file, "content_type", None)
            or mimetypes.guess_type(original_name or resolved_object_name)[0]
            or "application/octet-stream"
        )

        result = self.client.put_object(
            self.bucket_name,
            resolved_object_name,
            stream,
            length=length,
            content_type=content_type,
        )
        return {
            "object_name": resolved_object_name,
            "url": self.get_file_url(resolved_object_name),
            "etag": result.etag,
        }

    def download_file(self, object_name: str) -> bytes:
        response = self.client.get_object(
            self.bucket_name,
            self._normalize_object_name(object_name),
        )
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def get_file_url(self, object_name: str) -> str:
        return self.client.presigned_get_object(
            self.bucket_name,
            self._normalize_object_name(object_name),
            expires=DEFAULT_PRESIGNED_URL_EXPIRE,
        )

    def delete_file(self, object_name: str) -> None:
        self.client.remove_object(
            self.bucket_name,
            self._normalize_object_name(object_name),
        )

    @staticmethod
    def build_object_name(filename: str | None) -> str:
        safe_filename = Path(filename or "file").name
        suffix = "".join(Path(safe_filename).suffixes)
        stem = safe_filename[: -len(suffix)] if suffix else safe_filename
        cleaned_stem = re.sub(r"[^\w.-]+", "_", stem).strip("._-") or "file"
        dated_prefix = datetime.now().strftime("%Y/%m/%d")
        return f"{dated_prefix}/{uuid4().hex}_{cleaned_stem}{suffix}"

    @staticmethod
    def _normalize_object_name(object_name: str) -> str:
        return object_name.replace("\\", "/").lstrip("/")

    @staticmethod
    def _prepare_stream(file) -> tuple[object, int]:
        stream = getattr(file, "file", file)
        if hasattr(stream, "seek") and hasattr(stream, "tell"):
            stream.seek(0, 2)
            length = stream.tell()
            stream.seek(0)
            return stream, length

        payload = stream.read()
        buffer = BytesIO(payload)
        return buffer, len(payload)


def get_file_service() -> FileService:
    return FileService()
