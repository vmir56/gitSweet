# app/main.py
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

from app.core.config import settings
from app.core.database import engine, Base
from app.core.logging import setup_logging
from app.api.v1.endpoints import spider, ozon

# Настройка логирования
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan менеджер для управления ресурсами.
    Выполняется при старте и остановке приложения.
    """
    # Startup
    logger.info("🚀 Starting Spider Service...")
    
    # Создание таблиц в БД
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Инициализация пула браузеров (ленивая инициализация)
    from app.services.browser_pool import browser_pool
    await browser_pool.initialize()
    
    logger.info("✅ Spider Service started successfully!")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Spider Service...")
    
    # Закрытие всех браузеров
    await browser_pool.close_all()
    
    # Закрытие соединений с БД
    await engine.dispose()
    
    logger.info("✅ Spider Service stopped!")


# Создание приложения
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Spider Service for parsing product data from e-commerce websites",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# Настройка CORS
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Trusted Host
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"] if settings.DEBUG else settings.ALLOWED_HOSTS,
)

# Инструментарий для метрик (Prometheus)
if not settings.DEBUG:
    Instrumentator().instrument(app).expose(app)


# Регистрация роутеров
app.include_router(
    spider.router,
    prefix=settings.API_V1_PREFIX,
    tags=["spider"]
)
app.include_router(
    ozon.router,
    prefix=settings.API_V1_PREFIX,
    tags=["ozon"]
)


# Глобальные обработчики ошибок
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Глобальный обработчик исключений"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": str(exc) if settings.DEBUG else "Something went wrong",
        }
    )


# Health check
@app.get("/health")
async def health_check():
    """Проверка работоспособности сервиса"""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


# Корневой эндпоинт
@app.get("/")
async def root():
    """Корневой эндпоинт"""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs" if settings.DEBUG else None,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
    