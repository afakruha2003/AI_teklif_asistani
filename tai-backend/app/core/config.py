from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    
    DATABASE_URL: str = "postgresql+asyncpg://tai_user:tai_password@tai-db:5432/tai_db"
    
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-flash"
    
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "llama3-70b-8192"
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
            
        # Güvenli string kontrolü (None veya boş string olup olmadığını kontrol eder)
        has_gemini = bool(self.GEMINI_API_KEY and str(self.GEMINI_API_KEY).strip())
        has_openai = bool(self.OPENAI_API_KEY and str(self.OPENAI_API_KEY).strip())
        
        return has_gemini or has_openai

    class Config:
        env_file = ".env"
        extra = "ignore" # Frontend (.env'deki VITE_ vb.) değerlerini backendde yok sayar.

settings = Settings()