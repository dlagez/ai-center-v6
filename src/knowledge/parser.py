from pathlib import Path

from docling.document_converter import DocumentConverter

from src.knowledge.schemas import ParsedDocument


class DoclingParser:
    def __init__(self) -> None:
        # MVP stage: keep Docling on its default settings.
        self.converter = DocumentConverter()

    def parse(self, source: str | Path) -> ParsedDocument:
        result = self.converter.convert(source)
        doc = result.document

        return ParsedDocument(
            source=str(source),
            text=doc.export_to_markdown(),
        )
