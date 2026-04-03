from src.knowledge.chunker import chunk_document
from src.knowledge.schemas import ParsedDocument


def test_chunk_document_splits_markdown_by_headers() -> None:
    document = ParsedDocument(
        doc_id="doc-1",
        source="demo.md",
        markdown="# Title\n\nIntro text.\n\n## Section\n\nSection body.",
        text="Title\n\nIntro text.\n\nSection\n\nSection body.",
    )

    chunks = chunk_document(document, chunk_size=80, chunk_overlap=10)

    assert len(chunks) == 2
    assert chunks[0].headers == ["Title"]
    assert chunks[1].headers == ["Title", "Section"]
    assert "Section body." in chunks[1].text
