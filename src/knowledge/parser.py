import re
from hashlib import sha1
from pathlib import Path

from docling.document_converter import DocumentConverter

from src.knowledge.schemas import ParsedDocument


def markdown_to_text(markdown: str) -> str:
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", markdown)
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"[*_`>~]", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


class DoclingParser:
    def __init__(self) -> None:
        # MVP stage: keep Docling on its default settings.
        self.converter = DocumentConverter()

    def parse(self, source: str | Path) -> ParsedDocument:
        result = self.converter.convert(source)
        doc = result.document
        markdown = doc.export_to_markdown()
        source_str = str(source)

        return ParsedDocument(
            doc_id=sha1(source_str.encode("utf-8")).hexdigest(),
            source=source_str,
            markdown=markdown,
            text=markdown_to_text(markdown),
            metadata={"source_type": "docling"},
        )
