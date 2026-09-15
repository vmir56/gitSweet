# app/services/spider.py
import asyncio
import hashlib
import logging
from typing import List, Dict, Optional
from datetime import datetime
import aiohttp
from aiohttp import ClientTimeout, ClientError
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.product import Product
from app.models.source import Source
from app.models.history import History
from app.services.rate_limiter import RateLimiter
from app.services.proxy_manager import ProxyManager
from app.core.config import settings

logger = logging.getLogger(__name__)

class Spider:
    """
    Основной класс паука.
    Запускается по запросу пользователя для одного товара.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.rate_limiter = RateLimiter()
        self.proxy_manager = ProxyManager()
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Настройки поиска (можно вынести в конфиг)
        self.search_engines = settings.SEARCH_ENGINES  # Список магазинов
        self.max_sources = settings.MAX_SOURCES_PER_QUERY  # 10-20 магазинов
        
    async def __aenter__(self):
        """Создаем сессию с таймаутами"""
        timeout = ClientTimeout(
            total=30,      # Общий таймаут
            connect=10,    # Подключение
            sock_read=20   # Чтение
        )
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            headers=await self.proxy_manager.get_headers()
        )
        await self.rate_limiter.init_redis()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def search_product(self, query: str, user_id: int) -> Product:
        """
        Основная точка входа.
        Создает Product, ищет источники, парсит их.
        """
        # 1. Создаем запись о продукте
        product = Product(
            user_id=user_id,
            query=query,
            name=query  # Временно, потом нормализуем
        )
        self.db.add(product)
        await self.db.flush()
        
        # 2. Логируем начало поиска
        history = History(
            product_id=product.id,
            event_type='search',
            status='pending',
            message=f'Поиск товара: {query}'
        )
        self.db.add(history)
        await self.db.flush()
        
        try:
            # 3. Поиск по магазинам
            sources = await self._find_sources(query)
            
            # 4. Парсинг каждого источника
            parsed_sources = await self._parse_sources(sources)
            
            # 5. Сохраняем результаты
            for source_data in parsed_sources:
                source = Source(
                    product_id=product.id,
                    **source_data
                )
                self.db.add(source)
                
                # Логируем каждый источник
                history_item = History(
                    product_id=product.id,
                    source_id=source.id,
                    event_type='parse',
                    status='success',
                    message=f'Спарсено: {source_data["shop_name"]}',
                    snapshot={'price': source_data.get('price'), 'availability': source_data.get('availability')}
                )
                self.db.add(history_item)
            
            # 6. Обновляем статус поиска
            history.status = 'success'
            history.message = f'Найдено {len(parsed_sources)} источников'
            
            await self.db.commit()
            
        except Exception as e:
            # Логируем ошибку
            history.status = 'error'
            history.message = str(e)
            await self.db.commit()
            raise
        
        return product
    
    async def _find_sources(self, query: str) -> List[Dict]:
        """
        Поиск ссылок на товар в поисковых системах/магазинах.
        Здесь может быть интеграция с Google Search API, Yandex XML,
        или прямой поиск по сайтам.
        """
        sources = []
        
        # Пример: ищем на Ozon, Wildberries, Яндекс.Маркет
        shop_patterns = [
            {'name': 'Ozon', 'url': f'https://www.ozon.ru/search/?text={query}'},
            {'name': 'Wildberries', 'url': f'https://www.wildberries.ru/catalog/0/search.aspx?search={query}'},
            {'name': 'Яндекс.Маркет', 'url': f'https://market.yandex.ru/search?text={query}'},
        ]
        
        for shop in shop_patterns:
            # Проверяем rate limit перед запросом
            domain = shop['url'].split('/')[2]
            await self.rate_limiter.check_and_wait(domain)
            
            try:
                # Здесь должен быть реальный парсинг поисковой выдачи
                # Для демонстрации — возвращаем заглушку
                sources.append({
                    'shop_name': shop['name'],
                    'shop_url': shop['url'],
                    'product_url': shop['url'],  # В реальности — первая ссылка из выдачи
                })
                
            except Exception as e:
                logger.error(f"Ошибка поиска в {shop['name']}: {e}")
                continue
        
        return sources
    
    async def _parse_sources(self, sources: List[Dict]) -> List[Dict]:
        """
        Парсит каждый источник (извлекает цену, наличие, характеристики).
        С защитой от бана и rate limiting.
        """
        tasks = []
        for source in sources:
            task = self._parse_single_source(source)
            tasks.append(task)
        
        # Парсим параллельно, но с ограничением (не более 5 одновременно)
        semaphore = asyncio.Semaphore(5)
        async def limited_parse(task):
            async with semaphore:
                return await task
        
        results = await asyncio.gather(
            *[limited_parse(t) for t in tasks],
            return_exceptions=True
        )
        
        # Фильтруем ошибки
        parsed = []
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Ошибка парсинга {sources[idx]['shop_name']}: {result}")
                continue
            if result:
                parsed.append(result)
        
        return parsed
    
    async def _parse_single_source(self, source: Dict) -> Optional[Dict]:
        """
        Парсинг одного источника с exponential backoff.
        """
        domain = source['product_url'].split('/')[2]
        proxy = self.proxy_manager.get_proxy()
        
        for attempt in range(settings.MAX_RETRIES):
            try:
                # Rate limit перед каждым запросом
                await self.rate_limiter.check_and_wait(domain)
                
                # Выполняем запрос
                async with self.session.get(
                    source['product_url'],
                    proxy=proxy,
                    headers=await self.proxy_manager.get_headers()
                ) as response:
                    
                    # Проверка статуса
                    if response.status == 429:
                        logger.warning(f"429 Too Many Requests: {domain}")
                        await self._handle_429(domain)
                        continue
                    
                    if response.status == 503:
                        logger.warning(f"503 Service Unavailable: {domain}")
                        await self._handle_503(domain)
                        continue
                    
                    if response.status == 403:
                        logger.warning(f"403 Forbidden (бан): {domain}")
                        self.proxy_manager.mark_failed(proxy) if proxy else None
                        continue
                    
                    if response.status != 200:
                        logger.warning(f"HTTP {response.status}: {domain}")
                        continue
                    
                    # Читаем HTML
                    html = await response.text()
                    
                    # Парсим HTML
                    soup = BeautifulSoup(html, 'html.parser')
                    parsed_data = await self._extract_product_data(soup, source)
                    
                    if parsed_data:
                        # Добавляем метаданные
                        parsed_data['shop_name'] = source['shop_name']
                        parsed_data['shop_url'] = source['shop_url']
                        parsed_data['product_url'] = source['product_url']
                        
                        # Хэш для дедупликации
                        data_hash = hashlib.md5(
                            f"{source['shop_url']}{parsed_data.get('price', '')}".encode()
                        ).hexdigest()
                        parsed_data['raw_data'] = {'hash': data_hash}
                        
                        return parsed_data
                    
            except (ClientError, asyncio.TimeoutError) as e:
                logger.error(f"Ошибка запроса к {domain} (попытка {attempt+1}): {e}")
                if proxy:
                    self.proxy_manager.mark_failed(proxy)
                
                # Exponential backoff
                wait_time = 2 ** attempt  # 2, 4, 8, 16 секунд
                await asyncio.sleep(wait_time)
                
            except Exception as e:
                logger.error(f"Неожиданная ошибка {domain}: {e}")
                break
        
        return None
    
    async def _extract_product_data(self, soup: BeautifulSoup, source: Dict) -> Dict:
        """
        Извлечение данных из HTML.
        Здесь нужны XPath/CSS селекторы для каждого магазина.
        """
        # Это заглушка — в реальности для каждого магазина свой парсер
        try:
            # Пример для Ozon
            if 'ozon' in source['shop_url'].lower():
                price_elem = soup.select_one('[data-widget="webPrice"]')
                if price_elem:
                    price_text = price_elem.get_text().replace('₽', '').replace(' ', '').strip()
                    price = float(price_text) if price_text else None
                    
                    availability = soup.select_one('[data-widget="webStock"]')
                    in_stock = 'в наличии' in availability.get_text().lower() if availability else False
                    
                    return {
                        'price': price,
                        'old_price': None,
                        'currency': 'RUB',
                        'availability': in_stock,
                        'stock_count': None,
                    }
            
            # Пример для Wildberries
            if 'wildberries' in source['shop_url'].lower():
                # Сложный парсинг через JSON в скриптах
                # Для демонстрации
                return {
                    'price': 2990.0,
                    'old_price': 4990.0,
                    'currency': 'RUB',
                    'availability': True,
                    'stock_count': 15,
                }
                
        except Exception as e:
            logger.error(f"Ошибка извлечения данных: {e}")
        
        return None
    
    async def _handle_429(self, domain: str):
        """Обработка 429 — ждем 60 секунд"""
        wait_time = 60
        logger.warning(f"Rate limit для {domain}, ждем {wait_time} секунд")
        await asyncio.sleep(wait_time)
    
    async def _handle_503(self, domain: str):
        """Обработка 503 — ждем с экспоненциальным backoff"""
        wait_time = 10
        logger.warning(f"Сервер {domain} перегружен, ждем {wait_time} секунд")
        await asyncio.sleep(wait_time)