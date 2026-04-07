from pathlib import Path

from pydantic_settings import (
    BaseSettings,
    DotEnvSettingsSource,
    EnvSettingsSource,
    InitSettingsSource,
    PydanticBaseSettingsSource,
    SecretsSettingsSource,
    SettingsConfigDict,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "ai-center-v6"
    app_env: str = "development"
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    llm_default_model: str = "openai/gpt-4o"
    llm_vision_model: str = "dashscope/qwen-vl-plus-latest"
    llm_api_base: str | None = None
    dashscope_api_base: str | None = None
    dashscope_api_key: str | None = None
    llm_timeout: int = 60
    llm_temperature: float = 0.0
    media_ffmpeg_binary: str = "ffmpeg"
    media_frames_dir: str = "./data/media_frames"
    embedding_model: str = "openai/text-embedding-v3"
    embedding_batch_size: int = 32
    sql_agent_dialect: str = "sqlite"
    sql_agent_default_db_path: str | None = None
    sql_agent_max_rows: int = 20
    sql_agent_max_retries: int = 2
    sql_agent_mysql_host: str | None = None
    sql_agent_mysql_port: int = 3306
    sql_agent_mysql_user: str | None = None
    sql_agent_mysql_password: str | None = None
    sql_agent_mysql_database: str | None = None
    langfuse_enabled: bool = True
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_base_url: str = "https://cloud.langfuse.com"
    langfuse_debug: bool = False
    langfuse_flush_at: int = 1
    knowledge_chunk_size: int = 1200
    knowledge_chunk_overlap: int = 200
    qdrant_path: str = "./data/qdrant"
    qdrant_collection: str = "default_knowledge"
    embedding_dimension: int = 1536

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: InitSettingsSource,
        env_settings: EnvSettingsSource,
        dotenv_settings: DotEnvSettingsSource,
        file_secret_settings: SecretsSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            dotenv_settings,
            env_settings,
            file_secret_settings,
        )


settings = Settings()
