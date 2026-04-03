from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    source: str = Field(..., description="File or directory path to ingest.")


class SearchRequest(BaseModel):
    query: str = Field(..., description="User query for vector search.")
    limit: int = Field(default=5, ge=1, le=20, description="Maximum number of chunks to return.")
