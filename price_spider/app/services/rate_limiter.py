# app/services/rate_limiter.py
import asyncio
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, Tuple
import redis.asyncio as redis
from app.core.config import settings

class RateLimiter:
    """
    Распределенный rate limiter на Redis.
    Защищает от 429 и 503, не давая долбить один домен.
    """
    
    def __init__(self):
        self.redis = None
        self._local_cache: Dict[str, Tuple[int, float]] = defaultdict(lambda: (0, 0))
        
    async def init_redis(self):
        """Инициализация Redis (опционально, если нет Redis — работает локально)"""
        try:
            self.redis = await redis.from_url(settings.REDIS_URL, decode_responses=True)
        except:
            self.redis = None
    
    async def check_and_wait(self, domain: str) -> None:
        """
        Проверяет, можно ли делать запрос к домену.
        Если превышен лимит — ждет с экспоненциальной задержкой.
        """
        if self.redis:
            await self._check_redis(domain)
        else:
            await self._check_local(domain)
    
    async def _check_redis(self, domain: str):
        """Redis-based rate limiting"""
        key = f"rate_limit:{domain}"
        current = await self.redis.get(key)
        
        if current and int(current) >= settings.MAX_REQUESTS_PER_MINUTE:
            # Ждем до конца минуты
            ttl = await self.redis.ttl(key)
            wait_time = ttl + 1 if ttl > 0 else 60
            await asyncio.sleep(wait_time)
            
        # Инкрементим счетчик
        await self.redis.incr(key)
        await self.redis.expire(key, 60)  # Сброс через минуту
        
    async def _check_local(self, domain: str):
        """Локальный rate limiter (без Redis)"""
        now = time.time()
        count, window_start = self._local_cache[domain]
        
        # Если окно истекло (прошло более 60 сек)
        if now - window_start > 60:
            self._local_cache[domain] = (1, now)
            return
        
        # Если превышен лимит
        if count >= settings.MAX_REQUESTS_PER_MINUTE:
            wait_time = 60 - (now - window_start) + 1
            await asyncio.sleep(wait_time)
            self._local_cache[domain] = (1, time.time())
            return
        
        # Увеличиваем счетчик
        self._local_cache[domain] = (count + 1, window_start)