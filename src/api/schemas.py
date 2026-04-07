from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    source: str = Field(..., description="File or directory path to ingest.")


class SearchRequest(BaseModel):
    query: str = Field(..., description="User query for vector search.")
    limit: int = Field(default=5, ge=1, le=20, description="Maximum number of chunks to return.")


class AgenticRagRequest(BaseModel):
    question: str = Field(..., description="User question for agentic RAG.")
    limit: int = Field(default=5, ge=1, le=20, description="Maximum number of retrieved chunks.")


class SqlAgentRequest(BaseModel):
    question: str = Field(..., description="User question for the SQL agent.")
    dialect: str | None = Field(default=None, description="Database dialect: sqlite or mysql.")
    db_path: str | None = Field(default=None, description="SQLite database file path.")
    max_rows: int = Field(default=20, ge=1, le=100, description="Maximum number of rows to read.")


class VisionChatRequest(BaseModel):
    prompt: str = Field(..., description="User prompt for vision understanding.")
    image_url: str | None = Field(default=None, description="Public image URL or data URL.")
    image_path: str | None = Field(default=None, description="Local image file path on the server.")
    model: str | None = Field(
        default=None,
        description="Vision model name, e.g. dashscope/qwen-vl-plus-latest.",
    )
    max_tokens: int | None = Field(default=None, ge=1, le=8192, description="Maximum output tokens.")
