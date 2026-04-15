from fastapi.testclient import TestClient

from src.api.app import app
from src.storage.minio_client import MinioConfigError

client = TestClient(app)


def test_file_upload_endpoint_returns_upload_result(monkeypatch) -> None:
    class _FakeService:
        def upload_file(self, file, object_name=None):
            assert file.filename == "demo.txt"
            assert object_name is None
            return {
                "object_name": "2026/04/14/abc123_demo.txt",
                "url": "http://minio.local/demo.txt?token=1",
                "etag": "etag-123",
            }

    monkeypatch.setattr("src.api.routes.get_file_service", lambda: _FakeService())

    response = client.post(
        "/files/upload",
        files={"file": ("demo.txt", b"hello world", "text/plain")},
    )

    assert response.status_code == 200
    assert response.json() == {
        "object_name": "2026/04/14/abc123_demo.txt",
        "url": "http://minio.local/demo.txt?token=1",
        "etag": "etag-123",
    }


def test_file_upload_endpoint_maps_config_errors(monkeypatch) -> None:
    class _FakeService:
        def upload_file(self, file, object_name=None):
            raise MinioConfigError("MinIO is not configured.")

    monkeypatch.setattr("src.api.routes.get_file_service", lambda: _FakeService())

    response = client.post(
        "/files/upload",
        files={"file": ("demo.txt", b"hello world", "text/plain")},
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "MinIO is not configured."
