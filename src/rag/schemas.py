from pydantic import BaseModel, Field

from src.knowledge.schemas import SearchResult


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
