from pathlib import Path

from fastapi.testclient import TestClient

from src.api.app import app
from src.rag.schemas import IngestSummary

client = TestClient(app)


def test_ingest_endpoint_returns_summary(monkeypatch, tmp_path) -> None:
    source = tmp_path / "demo.pdf"
    source.write_text("placeholder", encoding="utf-8")

    class _FakeService:
        def ingest_path(self, source):
            assert Path(source) == source_path
            return IngestSummary(
                success=True,
                source=str(source),
                documents=1,
                chunks=3,
                collection="default_knowledge",
            )

    source_path = source
    monkeypatch.setattr("src.api.routes.KnowledgeIngestionService", lambda: _FakeService())

    response = client.post(
        "/knowledge/ingest",
        json={"source": str(source)},
    )

    assert response.status_code == 200
    assert response.json()["documents"] == 1
    assert response.json()["chunks"] == 3


def test_ingest_endpoint_maps_validation_errors(monkeypatch) -> None:
    class _FakeService:
        def ingest_path(self, source):
            raise ValueError("bad source")

    monkeypatch.setattr("src.api.routes.KnowledgeIngestionService", lambda: _FakeService())

    response = client.post("/knowledge/ingest", json={"source": "missing.pdf"})

    assert response.status_code == 400
    assert response.json()["detail"] == "bad source"
