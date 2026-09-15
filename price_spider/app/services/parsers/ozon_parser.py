# app/services/parsers/ozon_parser.py
import re
import asyncio
from typing import List, Dict, Optional
from app.services.playwright_base import PlaywrightBaseParser
import logging

logger = logging.getLogger(__name__)


class OzonParser(PlaywrightBaseParser):
    def __init__(self, headless: bool = False, proxy: Optional[str] = None):
        # Если headless не передан, берётся из HEADLESS (из .env)
        super().__init__(headless=headless, proxy=proxy)
        self.base_url = "https://www.ozon.ru"
        self.search_url = "https://www.ozon.ru/search/"

    async def search_product(self, query: str) -> List[Dict]:
        """Поиск товаров на Ozon"""
        if not self.page:
            logger.error("❌ Страница не инициализирована")
            return []

        search_url = f"{self.search_url}?text={query.replace(' ', '+')}"
        logger.info(f"🌐 Переход на {search_url}")

        try:
            # Переходим на страницу поиска
            await self.page.goto(search_url, timeout=60000)
            # Ждём полной загрузки динамического контента
            await self.page.wait_for_load_state("networkidle", timeout=30000)
            # Небольшая задержка для появления элементов
            await self.random_delay(2, 4)

            # Прокручиваем страницу, чтобы подгрузились карточки
            await self.human_like_scroll()

            # Ищем карточки несколькими селекторами
            card_selectors = [
                '[data-testid="cell"]',
                '.tile-root',
                '.product-card',
                '[data-testid="product-card"]',
                '.product-tile',
                '.item-card',
                'a[href*="/product/"]',
            ]

            cards = []
            for selector in card_selectors:
                found = await self.page.query_selector_all(selector)
                if found:
                    logger.info(f"✅ Найдено {len(found)} карточек по селектору: {selector}")
                    cards = found
                    break

            if not cards:
                logger.warning("⚠️ Карточки не найдены ни по одному селектору")
                # Сохраняем скриншот для отладки
                await self.take_screenshot("ozon_no_cards")
                return []

            results = []
            for idx, card in enumerate(cards[:10]):
                try:
                    # Название товара
                    title_elem = await card.query_selector('[data-testid="name"]')
                    if not title_elem:
                        # Пробуем другие варианты
                        title_elem = await card.query_selector('.tsBody500Medium, .product-card__title')
                    title = await title_elem.text_content() if title_elem else None
                    if not title:
                        continue

                    # Цена
                    price_elem = await card.query_selector('[data-testid="price"]')
                    if not price_elem:
                        price_elem = await card.query_selector('.tsHeadline500Medium, .product-card__price')
                    price_text = await price_elem.text_content() if price_elem else None
                    price = await self.extract_price(price_text) if price_text else None

                    # Ссылка
                    link_elem = await card.query_selector('a[href*="/product/"]')
                    link = await link_elem.get_attribute('href') if link_elem else None
                    product_url = f"{self.base_url}{link}" if link else None

                    results.append({
                        "title": title.strip(),
                        "price": price,
                        "price_text": price_text,
                        "url": product_url,
                    })
                    logger.info(f"  ✅ [{idx+1}] {title[:50]}... - {price_text}")
                except Exception as e:
                    logger.error(f"❌ Ошибка парсинга карточки {idx}: {e}")

            logger.info(f"✅ Найдено {len(results)} товаров")
            return results

        except Exception as e:
            logger.error(f"❌ Ошибка поиска: {e}")
            await self.take_screenshot("ozon_error")
            return []