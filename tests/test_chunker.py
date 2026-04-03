from src.knowledge.chunker import chunk_document
from src.knowledge.schemas import ParsedDocument


def test_chunk_document_returns_overlapping_chunks() -> None:
    document = ParsedDocument(source="demo.md", text="abcdefghij")

    chunks = chunk_document(document, chunk_size=4, chunk_overlap=1)

    assert [chunk.text for chunk in chunks] == ["abcd", "defg", "ghij"]
