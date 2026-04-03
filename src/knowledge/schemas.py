from typing import Any

from pydantic import BaseModel, Field


class ParsedDocument(BaseModel):
    doc_id: str
    source: str
    markdown: str = Field(default="", description="Markdown exported from Docling.")
    text: str = Field(default="", description="Plain text normalized from markdown.")
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


class IngestSummary(BaseModel):
    success: bool = True
    source: str
    documents: int
    chunks: int
    collection: str


class SearchSummary(BaseModel):
    query: str
    limit: int
    collection: str
    results: list[SearchResult] = Field(default_factory=list)
