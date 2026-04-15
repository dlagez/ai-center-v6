from minio import Minio

from src.config.settings import settings

REQUIRED_MINIO_FIELDS = {
    "MINIO_ENDPOINT": "minio_endpoint",
    "MINIO_ACCESS_KEY": "minio_access_key",
    "MINIO_SECRET_KEY": "minio_secret_key",
    "MINIO_BUCKET": "minio_bucket",
}


class MinioConfigError(RuntimeError):
    """Raised when MinIO configuration is missing or incomplete."""


def _is_blank(value: str | None) -> bool:
    return value is None or not str(value).strip()


def is_minio_enabled() -> bool:
    configured_fields = [
        env_name
        for env_name, attr_name in REQUIRED_MINIO_FIELDS.items()
        if not _is_blank(getattr(settings, attr_name))
    ]
    if not configured_fields:
        return False
    if len(configured_fields) != len(REQUIRED_MINIO_FIELDS):
        missing_fields = [
            env_name
            for env_name, attr_name in REQUIRED_MINIO_FIELDS.items()
            if _is_blank(getattr(settings, attr_name))
        ]
        raise MinioConfigError(
            "MinIO configuration is incomplete. Missing: " + ", ".join(missing_fields)
        )
    return True


def get_minio_client() -> Minio:
    if not is_minio_enabled():
        raise MinioConfigError("MinIO is not configured.")

    return Minio(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


def ensure_minio_bucket() -> None:
    if not is_minio_enabled():
        return

    client = get_minio_client()
    bucket_name = settings.minio_bucket
    if not client.bucket_exists(bucket_name):
        client.make_bucket(bucket_name)
