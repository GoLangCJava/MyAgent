import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/deep_platform")
    SYNC_DATABASE_URL: str = os.getenv("SYNC_DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/deep_platform")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    JWT_SECRET: str = os.getenv("JWT_SECRET", "dev-super-secret-jwt-key-change-in-prod")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))
    ARQ_MAX_JOBS: int = int(os.getenv("ARQ_MAX_JOBS", "10"))
    DEFAULT_MODEL: str = os.getenv("DEFAULT_MODEL", "openai:gpt-4o-mini")
    WORKSPACE_BASE: str = os.getenv("WORKSPACE_BASE", "/tmp/workspaces")
    RUN_CANCEL_TTL: int = int(os.getenv("RUN_CANCEL_KEY_TTL_SECONDS", "1800"))
    RUN_STREAM_TTL: int = int(os.getenv("RUN_EVENTS_STREAM_TTL_SECONDS", "7200"))
    RUN_STREAM_MAXLEN: int = int(os.getenv("RUN_EVENTS_STREAM_MAXLEN", "0"))

settings = Settings()
