from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ==========================
    # Application Settings
    # ==========================
    APP_NAME: str = "ProspectusAI"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = True

    # ==========================
    # Groq
    # ==========================
    GROQ_API_KEY: str = ""

    # ==========================
    # Qdrant
    # ==========================
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333

    # ==========================
    # AI Models
    # ==========================
    EMBEDDING_MODEL: str = "BAAI/bge-m3"
    RERANKER_MODEL: str = "BAAI/bge-reranker-v2-m3"
   # Document Classification
    TEXT_THRESHOLD: int = 50
    # Load values from .env
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()