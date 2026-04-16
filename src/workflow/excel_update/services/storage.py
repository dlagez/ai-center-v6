from __future__ import annotations

import hashlib
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from src.config.settings import settings
from src.storage.file_service import FileService
from src.storage.minio_client import is_minio_enabled


@dataclass(slots=True)
class StoredObject:
    bucket_name: str
    object_key: str
    file_size: int
    checksum_md5: str


class ExcelStorageService:
    def __init__(self):
        self.bucket_name = settings.minio_bucket or "local"
        self.local_root = Path(settings.excel_update_output_dir).resolve() / "objects"

    def save_bytes(
        self,
        *,
        payload: bytes,
        object_key: str,
        content_type: str = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ) -> StoredObject:
        if is_minio_enabled():
            stream = BytesIO(payload)
            file_service = FileService(self.bucket_name)
            file_service.client.put_object(
                file_service.bucket_name,
                object_key,
                stream,
                length=len(payload),
                content_type=content_type,
            )
            bucket_name = file_service.bucket_name
        else:
            target_path = self.local_root / object_key
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_bytes(payload)
            bucket_name = self.bucket_name
        return StoredObject(
            bucket_name=bucket_name,
            object_key=object_key,
            file_size=len(payload),
            checksum_md5=hashlib.md5(payload).hexdigest(),
        )

    def download_bytes(self, object_key: str) -> bytes:
        if is_minio_enabled():
            return FileService(self.bucket_name).download_file(object_key)
        return (self.local_root / object_key).read_bytes()

    def delete_object(self, object_key: str) -> None:
        if is_minio_enabled():
            FileService(self.bucket_name).delete_file(object_key)
            return
        target_path = self.local_root / object_key
        if target_path.exists():
            target_path.unlink()
