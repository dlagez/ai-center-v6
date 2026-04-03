from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    source: str = Field(..., description="File or directory path to ingest.")
    embedding_model: str | None = Field(default=None, description="Optional embedding model override.")
