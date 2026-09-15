# app/services/proxy_manager.py
import random
from typing import Optional
import aiohttp
from app.core.config import settings

class ProxyManager:
    """
    Управление прокси с ротацией и проверкой работоспособности.
    """
    
    def __init__(self):
        self.proxies = settings.PROXY_LIST  # Список прокси из .env
        self.current_index = 0
        self._failed_proxies = set()
        
    def get_proxy(self) -> Optional[str]:
        """Возвращает случайный рабочий прокси"""
        available = [p for p in self.proxies if p not in self._failed_proxies]
        if not available:
            # Если все прокси упали — пробуем без прокси
            return None
        
        return random.choice(available)
    
    def mark_failed(self, proxy: str):
        """Помечает прокси как нерабочий"""
        self._failed_proxies.add(proxy)
        # Можно добавить логику повторной проверки через N минут
    
    async def get_headers(self) -> dict:
        """Ротация User-Agent и заголовков"""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
        ]
        
        return {
            'User-Agent': random.choice(user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
        }