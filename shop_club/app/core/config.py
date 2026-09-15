# shop_club/app/core/config.py
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, AnyHttpUrl


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # ========== ОСНОВНЫЕ НАСТРОЙКИ ==========
    APP_NAME: str = "Shop Club"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    
    # ========== API ==========
    API_V1_PREFIX: str = "/api/v1"
    #👇 JWT-КЛЮЧ
    SECRET_KEY: str = "LU-lIp6tG3DKOTCPVohhHwagrm-CBF0mkJ6qmeHEGcs"  # 👈 СОВПАДАЕТ С auth.py
    ALLOWED_HOSTS: List[str] = ["*"]
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []
    
    # ========== JWT ==========
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # ========== БАЗА ДАННЫХ ==========
    # DATABASE_URL: str = "postgresql+asyncpg://v.ant@localhost:5432/shop_club_db"
    DATABASE_URL: str = "postgresql+asyncpg://v.ant@host.docker.internal:5432/shop_club_db"

    # ========== ПОДКЛЮЧЕНИЕ К PRICE_SPIDER ==========
    # SPIDER_URL: str = "http://localhost:8001"
    SPIDER_URL: str = "http://price_spider:8001"
    SPIDER_API_KEYS: str = "shop_club_2026_7f2k9m8q"
    SPIDER_TIMEOUT: int = 120
    
    # ========== КЕШИРОВАНИЕ ==========
    REDIS_URL: Optional[str] = None
    CACHE_TTL: int = 3600
    
    # ========== ПАГИНАЦИЯ ==========
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100


settings = Settings()