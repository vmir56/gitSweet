# price_spider/app/api/v1/endpoints/__init__.py
from fastapi import Depends, HTTPException, Security, Request
from fastapi.security import APIKeyHeader
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def validate_api_key(
    request: Request,
    api_key: str = Security(api_key_header)
):
    """
    Проверка API Key. Поддерживает несколько ключей.
    """
    # 👇 ЛОГИРУЕМ ВСЁ, ЧТО ПРИШЛО
    logger.info(f"🔑 Получен API Key: '{api_key}'")
    logger.info(f"📋 Ожидаемые ключи: {settings.SPIDER_API_KEYS}")
    logger.info(f"📋 Тип ожидаемых ключей: {type(settings.SPIDER_API_KEYS)}")
    
    if not api_key:
        logger.warning("❌ API Key отсутствует в заголовке")
        raise HTTPException(
            status_code=401,
            detail="API Key required. Please provide X-API-Key header."
        )
    
    # Проверяем, есть ли ключ в списке разрешённых
    if api_key not in settings.SPIDER_API_KEYS:
        logger.warning(f"❌ Неверный ключ: '{api_key}'")
        logger.warning(f"❌ Ожидались: {settings.SPIDER_API_KEYS}")
        raise HTTPException(
            status_code=403,
            detail=f"Invalid API Key. Access denied. Expected one of: {settings.SPIDER_API_KEYS}"
        )
    
    logger.info(f"✅ API Key от {api_key} принят")
    return api_key

# Опционально: проверка, что запрос приходит от доверенного сервиса
async def validate_internal_request(api_key: str = Security(api_key_header)):
    """То же самое, но с другим названием для читаемости кода"""
    return await validate_api_key(api_key)
