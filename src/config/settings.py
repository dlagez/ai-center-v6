from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "ai-center-v6"
    app_env: str = "development"
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    llm_default_model: str = "openai/gpt-4o"
    llm_api_base: str | None = None
    llm_timeout: int = 60
    llm_temperature: float = 0.0
    qdrant_path: str = "./data/qdrant"
    qdrant_collection: str = "default_knowledge"
    embedding_dimension: int = 1536


settings = Settings()
