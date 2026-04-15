from src.storage import minio_client


def test_ensure_minio_bucket_creates_bucket_when_missing(monkeypatch) -> None:
    created_buckets = []

    class _FakeClient:
        def bucket_exists(self, bucket_name: str) -> bool:
            assert bucket_name == "test-bucket"
            return False

        def make_bucket(self, bucket_name: str) -> None:
            created_buckets.append(bucket_name)

    monkeypatch.setattr(minio_client, "is_minio_enabled", lambda: True)
    monkeypatch.setattr(minio_client, "get_minio_client", lambda: _FakeClient())
    monkeypatch.setattr(minio_client.settings, "minio_bucket", "test-bucket")

    minio_client.ensure_minio_bucket()

    assert created_buckets == ["test-bucket"]


def test_ensure_minio_bucket_skips_when_storage_is_disabled(monkeypatch) -> None:
    monkeypatch.setattr(minio_client, "is_minio_enabled", lambda: False)
    monkeypatch.setattr(
        minio_client,
        "get_minio_client",
        lambda: (_ for _ in ()).throw(AssertionError("client should not be created")),
    )

    minio_client.ensure_minio_bucket()
