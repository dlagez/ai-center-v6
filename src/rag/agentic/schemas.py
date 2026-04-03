from typing import Any

from pydantic import BaseModel, Field
from typing_extensions import TypedDict

from src.knowledge.schemas import SearchResult


class AgenticRagInput(BaseModel):
    question: str
    limit: int = Field(default=5, ge=1, le=20)


class AgenticRagOutput(BaseModel):
    question: str
    answer: str
    retrieval_attempts: int
    retrieval_query: str
    sources: list[SearchResult] = Field(default_factory=list)
    trace_id: str | None = None
    trace_url: str | None = None


class AgenticRagState(TypedDict, total=False):
    question: str
    limit: int
    route: str
    rewrite_needed: bool
    rewritten_question: str
    retrieval_query: str
    retrieval_attempts: int
    retrieved_docs: list[SearchResult]
    answer: str
    sources: list[SearchResult]
    metadata: dict[str, Any]
