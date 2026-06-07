from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):

    DATABASE_URL: str = "postgresql+asyncpg://tai_user:tai_password@tai-db:5432/tai_db"

    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_BASE_URL: Optional[str] = None

    LLM_ENABLED: bool = True
    ENABLE_STREAMING: bool = True
    ENABLE_IDEMPOTENCY: bool = True

    SECRET_KEY: str = "changeme"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost,http://localhost:3000,http://localhost:8080"

    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_DAY: int = 1000

    SEED_ON_STARTUP: bool = True

    @property
    def llm_enabled(self) -> bool:
        if not self.LLM_ENABLED:
            return False
        return bool(self.OPENAI_API_KEY and str(self.OPENAI_API_KEY).strip())

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()