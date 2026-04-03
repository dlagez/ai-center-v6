from pydantic import BaseModel, Field


class ParsedDocument(BaseModel):
    source: str
    text: str = Field(default="", description="Markdown exported from Docling.")


class DocumentChunk(BaseModel):
    source: str
    index: int
    text: str
