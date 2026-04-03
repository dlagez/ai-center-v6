from pathlib import Path

from src.knowledge.indexer import QdrantIndexer
from src.knowledge.parser import DoclingParser
from src.knowledge.schemas import IngestSummary

SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".pptx",
    ".md",
    ".html",
    ".htm",
    ".png",
    ".jpg",
    ".jpeg",
}


def iter_supported_sources(path: Path) -> list[Path]:
    if path.is_file():
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {path.suffix}")
        return [path]

    if not path.exists():
        raise ValueError(f"Source path does not exist: {path}")
    if not path.is_dir():
        raise ValueError(f"Source path is not a file or directory: {path}")

    return sorted(
        candidate
        for candidate in path.rglob("*")
        if candidate.is_file() and candidate.suffix.lower() in SUPPORTED_EXTENSIONS
    )


class KnowledgeIngestionService:
    def __init__(
        self,
        parser: DoclingParser | None = None,
        indexer: QdrantIndexer | None = None,
    ) -> None:
        self.parser = parser or DoclingParser()
        self.indexer = indexer or QdrantIndexer()

    def ingest_path(
        self,
        source: str | Path,
        embedding_model: str | None = None,
    ) -> IngestSummary:
        source_path = Path(source)
        if not source_path.exists():
            raise ValueError(f"Source path does not exist: {source_path}")

        sources = iter_supported_sources(source_path)
        if not sources:
            raise ValueError(f"No supported documents found under: {source_path}")

        documents = 0
        chunks = 0
        for item in sources:
            parsed = self.parser.parse(item)
            indexed_chunks = self.indexer.index_document(parsed, embedding_model=embedding_model)
            documents += 1
            chunks += len(indexed_chunks)

        return IngestSummary(
            success=True,
            source=str(source_path),
            documents=documents,
            chunks=chunks,
            collection=self.indexer.store.collection_name,
        )
