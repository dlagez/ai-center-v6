from typing import Any

from docling_core.types.doc import DoclingDocument
from pydantic import BaseModel, ConfigDict, Field


class ParsedDocument(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    doc_id: str
    source: str
    markdown: str = Field(default="", description="Markdown exported from Docling.")
    text: str = Field(default="", description="Plain text normalized from markdown.")
    docling_document: DoclingDocument | None = Field(default=None, description="Native Docling document.")
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentChunk(BaseModel):
    id: str
    doc_id: str
    source: str
    index: int
    markdown: str
    text: str
    headers: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResult(BaseModel):
    id: str
    doc_id: str
    source: str
    index: int
    text: str
    score: float
    headers: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
