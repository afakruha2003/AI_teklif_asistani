from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # --- Veritabanı ---
    DATABASE_URL: str = "postgresql+asyncpg://tai_user:tai_password@tai-db:5432/tai_db"
    
    # --- Yapay Zeka (LLM) Ayarları ---
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-flash"
    
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "llama3-70b-8192"
    OPENAI_BASE_URL: Optional[str] = None
    
    # Video çekimi için en önemli özellik! .env dosyasından okunur.
    LLM_ENABLED: bool = True 
    ENABLE_STREAMING: bool = True
    ENABLE_IDEMPOTENCY: bool = True

    # --- Güvenlik & JWT ---
    SECRET_KEY: str = "changeme"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # --- Sunucu & Uygulama ---
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost,http://localhost:3000,http://localhost:8080"
    
    # --- Rate Limiting ---
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_DAY: int = 1000

    SEED_ON_STARTUP: bool = True

    # Backend'in diğer yerleri hala "settings.llm_enabled" kontrolü yapıyor. 
    # Bu metotla hem kodun bozulmamasını hem de videoda tek tuşla kapatabilmeni sağlıyoruz.
    @property
    def llm_enabled(self) -> bool:
        # 1. Eğer sen .env içinden bilerek LLM_ENABLED=false yaptıysan, AI direkt KAPANIR (Video için)
        if not self.LLM_ENABLED:
            return False
            
        # 2. LLM_ENABLED=true ise bile, sistem güvenlik için anahtarın girilip girilmediğine bakar
        has_gemini = bool(self.GEMINI_API_KEY and self.GEMINI_API_KEY.strip())
        has_openai = bool(self.OPENAI_API_KEY and self.OPENAI_API_KEY.strip())
        
        return has_gemini or has_openai

    class Config:
        env_file = ".env"
        extra = "ignore" # Frontend (.env'deki VITE_ vb.) değerlerini backendde yok sayar.

settings = Settings()