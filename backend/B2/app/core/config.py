from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # PostgreSQL
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/date_course_db"
    DATABASE_SYNC_URL: str = "postgresql+psycopg2://postgres:password@localhost:5432/date_course_db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Anthropic
    ANTHROPIC_API_KEY: str = ""

    # OpenAI (임베딩 — text-embedding-3-small)
    OPENAI_API_KEY: str = ""

    # Qdrant
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333

    # Meilisearch
    MEILISEARCH_URL: str = "http://localhost:7700"
    MEILISEARCH_MASTER_KEY: str = ""

    # Naver Local Search API
    NAVER_CLIENT_ID: str = ""
    NAVER_CLIENT_SECRET: str = ""

    # Kakao Local API
    KAKAO_REST_API_KEY: str = ""

    # JWT
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30


settings = Settings()
