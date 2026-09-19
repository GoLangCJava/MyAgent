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
    # 默认模型: SiliconFlow Qwen (OpenAI 兼容接口)
    DEFAULT_MODEL: str = os.getenv("DEFAULT_MODEL", "siliconflow:Qwen/Qwen2.5-7B-Instruct")
    WORKSPACE_BASE: str = os.getenv("WORKSPACE_BASE", "/tmp/workspaces")
    RUN_CANCEL_TTL: int = int(os.getenv("RUN_CANCEL_KEY_TTL_SECONDS", "1800"))
    RUN_STREAM_TTL: int = int(os.getenv("RUN_EVENTS_STREAM_TTL_SECONDS", "7200"))
    RUN_STREAM_MAXLEN: int = int(os.getenv("RUN_EVENTS_STREAM_MAXLEN", "0"))

    # ---- LLM 提供商配置 (OpenAI 兼容) ----
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    # SiliconFlow (https://siliconflow.cn) OpenAI 兼容接口
    SILICONFLOW_API_KEY: str = os.getenv("SILICONFLOW_API_KEY", "")
    SILICONFLOW_BASE_URL: str = os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1")

    def resolve_provider_config(self, provider: str) -> tuple[str, str]:
        """返回 (api_key, base_url)。base_url 为空表示用官方默认。"""
        p = (provider or "").lower().strip()
        if p in ("siliconflow", "silicon", "qwen"):
            api_key = self.SILICONFLOW_API_KEY or self.OPENAI_API_KEY
            base_url = self.SILICONFLOW_BASE_URL or self.OPENAI_BASE_URL or "https://api.siliconflow.cn/v1"
            return api_key, base_url
        if p in ("openai", ""):
            return self.OPENAI_API_KEY or self.SILICONFLOW_API_KEY, self.OPENAI_BASE_URL
        if p == "anthropic":
            return self.ANTHROPIC_API_KEY, ""
        # 通用 OpenAI 兼容提供商: 优先 {PROVIDER}_API_KEY / {PROVIDER}_BASE_URL
        env_prefix = p.upper().replace("-", "_")
        api_key = os.getenv(f"{env_prefix}_API_KEY", "") or self.OPENAI_API_KEY
        base_url = os.getenv(f"{env_prefix}_BASE_URL", "") or self.OPENAI_BASE_URL
        return api_key, base_url


settings = Settings()
