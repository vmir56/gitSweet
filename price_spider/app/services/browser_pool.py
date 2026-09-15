# app/services/browser_pool.py
import asyncio
import os
from typing import Optional, List
from contextlib import asynccontextmanager
from playwright.async_api import async_playwright, Browser, BrowserContext
import logging

logger = logging.getLogger(__name__)

BROWSER_TYPE = os.getenv("PLAYWRIGHT_BROWSER", "chromium")
HEADLESS = os.getenv("OZON_HEADLESS", "True").lower() == "true"
# USER_DATA_DIR = os.getenv("CHROMIUM_PROFILE_PATH", "/Users/v.ant/mk/vs/price_spider/chrome_profile")
USER_DATA_DIR = '/app/chrome_profile_docker'
os.makedirs(USER_DATA_DIR, exist_ok=True)


class BrowserPool:
    _instance = None
    _browsers: List[Browser] = []
    _contexts: List[BrowserContext] = []  # 👈 ДОБАВЛЯЕМ _contexts
    _max_browsers = 3
    _lock = asyncio.Lock()
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def initialize(self, max_browsers: int = 3):
        if self._initialized:
            return
        self._max_browsers = max_browsers
        self._initialized = True
        logger.info(f"✅ BrowserPool initialized with {BROWSER_TYPE}, max {max_browsers} browsers")

    @asynccontextmanager
    async def browser_session(self):
        """Контекстный менеджер для работы с браузером"""
        playwright = None
        context = None
        try:
            playwright = await async_playwright().start()
            context = await playwright.chromium.launch_persistent_context(
                user_data_dir=USER_DATA_DIR,
                headless=HEADLESS,
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                ignore_default_args=["--enable-automation"],
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--start-maximized",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-setuid-sandbox",
                    "--disable-web-security",
                    "--disable-features=IsolateOrigins,site-per-process",
                    "--disable-gpu",
                    "--disable-software-rasterizer",
                ],
                viewport={'width': 1920, 'height': 1080},
                locale='ru-RU',
                timezone_id='Europe/Moscow',
            )
            self._contexts.append(context)  # 👈 ТЕПЕРЬ _contexts СУЩЕСТВУЕТ
            yield context
        finally:
            if context:
                await context.close()
                if context in self._contexts:
                    self._contexts.remove(context)
            if playwright:
                await playwright.stop()

    async def close_all(self):
        """Закрытие всех браузеров и контекстов"""
        logger.info(f"🛑 Closing {len(self._contexts)} contexts and {len(self._browsers)} browsers...")
        
        # Закрываем все контексты
        for context in self._contexts:
            try:
                await context.close()
            except Exception as e:
                logger.error(f"❌ Error closing context: {e}")
        self._contexts.clear()
        
        # Закрываем все браузеры
        for browser in self._browsers:
            try:
                await browser.close()
            except Exception as e:
                logger.error(f"❌ Error closing browser: {e}")
        self._browsers.clear()
        
        logger.info("✅ All browsers and contexts closed")


browser_pool = BrowserPool()