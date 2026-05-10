from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    solar_api_key: str = Field(default="", alias="SOLAR_API_KEY")
    solar_base_url: str = Field(
        default="https://api.upstage.ai/v1", alias="SOLAR_BASE_URL"
    )

    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@db:5432/somagame",
        alias="DATABASE_URL",
    )

    session_cookie_name: str = Field(default="session_id", alias="SESSION_COOKIE_NAME")
    session_cookie_secure: bool = Field(default=False, alias="SESSION_COOKIE_SECURE")
    session_cookie_samesite: str = Field(default="lax", alias="SESSION_COOKIE_SAMESITE")
    session_ttl_hours: int = Field(default=24, alias="SESSION_TTL_HOURS")

    allowed_origins: str = Field(
        default="http://127.0.0.1:5500,http://localhost:5500",
        alias="ALLOWED_ORIGINS",
    )

    chat_limit_default: int = Field(default=25, alias="CHAT_LIMIT_DEFAULT")
    llm_model: str = Field(default="solar-pro3", alias="LLM_MODEL")
    embedding_model: str = Field(default="embedding-passage", alias="EMBEDDING_MODEL")
    embedding_query_model: str = Field(
        default="embedding-query", alias="EMBEDDING_QUERY_MODEL"
    )
    embedding_dim: int = Field(default=4096, alias="EMBEDDING_DIM")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
