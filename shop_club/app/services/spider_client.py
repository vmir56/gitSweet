# shop_club/app/services/spider_client.py
import httpx
import asyncio
from typing import Optional, Dict, Any, List
from app.core.config import settings
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


class SpiderClient:
    """
    Клиент для взаимодействия с микросервисом price_spider.
    Поддерживает авторизацию через API Key, таймауты и обработку ошибок.
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: Optional[int] = None
    ):
        self.base_url = base_url or settings.SPIDER_URL
        self.api_key = api_key or settings.SPIDER_API_KEYS
        self.timeout = timeout or settings.SPIDER_TIMEOUT
        self._client = None
    
    @property
    def headers(self) -> Dict[str, str]:
        """Заголовки для авторизации в price_spider"""
        return {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key,
            "Accept": "application/json",
        }
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Получение HTTP клиента с таймаутом"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                follow_redirects=True,
            )
        return self._client
    
    async def close(self):
        """Закрытие HTTP клиента"""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    # ========== ОСНОВНЫЕ МЕТОДЫ ==========
    
    async def search_product(
        self, 
        query: str, 
        max_results: int = 5, 
        user_id: int = 1
    ) -> Dict[str, Any]:
        """
        Поиск товара на Ozon через price_spider.
        
        Args:
            query: Поисковый запрос
            max_results: Максимальное количество результатов
            user_id: ID пользователя в shop_club
            
        Returns:
            Dict с результатами поиска
        """
        client = await self._get_client()
        
        try:
            response = await client.post(
                f"{self.base_url}/api/v1/ozon/search",
                headers=self.headers,
                json={
                    "query": query,
                    "max_results": max_results,
                    "user_id": user_id
                }
            )
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from price_spider: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Price Spider error: {e.response.status_code} - {e.response.text}")
        except httpx.TimeoutException as e:
            logger.error(f"Timeout waiting for price_spider: {e}")
            raise Exception("Price Spider timeout. Try again later.")
        except Exception as e:
            logger.error(f"Unexpected error from price_spider: {e}")
            raise
    
    async def search_ozon_direct(self, query: str, max_results: int = 5) -> List[Dict]:
        """
        Поиск на Ozon с возвратом только списка товаров.
        Удобно для использования в карточках товаров.
        """
        result = await self.search_product(query, max_results)
        return result.get("results", [])
    
    async def get_parse_status(self, product_id: int) -> Dict[str, Any]:
        """
        Получение статуса парсинга по ID товара.
        """
        client = await self._get_client()
        
        try:
            response = await client.get(
                f"{self.base_url}/api/v1/spider/status/{product_id}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from price_spider: {e.response.status_code}")
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return {"error": str(e)}
    
    async def health_check(self) -> bool:
        """
        Проверка доступности price_spider.
        """
        try:
            client = await self._get_client()
            response = await client.get(
                f"{self.base_url}/health",
                timeout=5.0
            )
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False


# ========== СИНГЛТОН ДЛЯ ИСПОЛЬЗОВАНИЯ В ПРИЛОЖЕНИИ ==========

_spider_client: Optional[SpiderClient] = None

def get_spider_client() -> SpiderClient:
    """Получение экземпляра клиента (синглтон)"""
    global _spider_client
    if _spider_client is None:
        _spider_client = SpiderClient()
    return _spider_client