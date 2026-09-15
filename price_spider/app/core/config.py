# app/core/config.py
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, AnyHttpUrl


class Settings(BaseSettings):
    """Настройки приложения"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # Application
    APP_NAME: str = "Spider Service"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    
    # API
    SPIDER_API_KEYS: List[str] = []
    API_V1_PREFIX: str = "/api/v1"
    SECRET_KEY: str = "NFwAqX8QoNLzGd_kTa4xTzU4BG6g6js46xBOJf7ZzQ4"
    ALLOWED_HOSTS: List[str] = ["*"]
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []
    
    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str) and v:
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v or []
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://v.ant@localhost:5432/spider_db"
    REDIS_URL: Optional[str] = None
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 60
    MAX_REQUESTS_PER_MINUTE: int = 10
    MAX_RETRIES: int = 3
    MAX_SOURCES_PER_QUERY: int = 20
    REQUEST_TIMEOUT: int = 30
    
    # Proxy - ГЛАВНЫЙ ФИКС ЗДЕСЬ
    PROXY_LIST: List[str] = []  # 👈 Значение по умолчанию - пустой список
    
    @field_validator("PROXY_LIST", mode="before")
    @classmethod
    def parse_proxy_list(cls, v):
        """Безопасный парсинг прокси"""
        if v is None:
            return []
        if isinstance(v, str):
            v = v.strip()
            if not v or v in ["[]", "()", ""]:
                return []
            return [p.strip() for p in v.split(",") if p.strip()]
        if isinstance(v, list):
            return v
        return []
    
    # Ozon Parser

    OZON_HEADLESS: bool = True  # 👈 False для отладки
    OZON_TIMEOUT: int = 30000
    OZON_MAX_RETRIES: int = 3
    OZON_DELAY_BETWEEN_REQUESTS: float = 2.0
    OZON_SAVE_SCREENSHOTS: bool = False
    OZON_SAVE_HTML: bool = False
    
    # Wildberries Parser

    WB_HEADLESS: bool = False  # 👈 False для отладки
    WB_TIMEOUT: int = 30000
    
    # Разрешенные origins для CORS (если shop_club на другом порту)
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:8000",  # shop_club
        "http://127.0.0.1:8000",
    ]
    
# Создаем глобальный экземпляр
settings = Settings()