from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    source: str = Field(..., description="File or directory path to ingest.")
