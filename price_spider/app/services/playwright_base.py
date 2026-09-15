# app/services/playwright_base.py
import os
import random
import re
import asyncio
from typing import Optional, Dict, List, Any
from playwright.async_api import async_playwright, Browser, Page, BrowserContext
import logging

logger = logging.getLogger(__name__)

# Настройки
BROWSER_TYPE = os.getenv("PLAYWRIGHT_BROWSER", "chromium")
# HEADLESS = os.getenv("OZON_HEADLESS", "False").lower() == "true"
USER_DATA_DIR = os.getenv("CHROMIUM_PROFILE_PATH", "/Users/v.ant/mk/vs/price_spider/chrome_profile")
os.makedirs(USER_DATA_DIR, exist_ok=True)


class PlaywrightBaseParser:
    def __init__(self, headless: bool = True, proxy: Optional[str] = None, browser=None):
        self.headless = headless
        self.proxy = proxy
        self.browser = browser
        self.page: Optional[Page] = None
        self.context: Optional[BrowserContext] = None
        self.playwright = None
        self._owns_browser = False

    async def __aenter__(self):
        try:
            if not self.browser:
                self._owns_browser = True
                self.playwright = await async_playwright().start()

                logger.info(f"🔥 Запуск Chromium с профилем: {USER_DATA_DIR}")
                self.context = await self.playwright.chromium.launch_persistent_context(
                    user_data_dir=USER_DATA_DIR,
                    headless=self.headless,
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
                    extra_http_headers={
                        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Cache-Control': 'max-age=0',
                        'Connection': 'keep-alive',
                        'DNT': '1',
                        'Upgrade-Insecure-Requests': '1',
                    }
                )
                self.browser = self.context
                if self.context.pages:
                    self.page = self.context.pages[0]
                else:
                    self.page = await self.context.new_page()

                await self._apply_stealth()
                logger.info(f"✅ Браузер инициализирован (headless={self.headless})")
            return self
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации: {e}")
            raise

    async def _apply_stealth(self):
        """Применяет маскировку: пробует библиотеку, иначе ручную."""
        if not self.page:
            return
        '''
        # Пробуем импортировать и использовать библиотеку
        try:
            from playwright_stealth import stealth_async
            await stealth_async(self.page)
            logger.info("✅ Stealth (async) применён")
            return
        except (ImportError, AttributeError):
            pass

        # Альтернативный способ через класс Stealth
        try:
            from playwright_stealth import Stealth
            stealth = Stealth()
            if hasattr(stealth, 'apply_async'):
                await stealth.apply_async(self.page)
            elif hasattr(stealth, 'apply'):
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, stealth.apply, self.page)
            else:
                try:
                    await Stealth(self.page).apply_stealth()
                except:
                    raise ImportError
            logger.info("✅ Stealth (через класс) применён")
            return
        except (ImportError, AttributeError):
            pass
        '''
        # Ручная маскировка (fallback)
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = {
                runtime: {},
                loadTimes: () => {},
                csi: () => {},
                app: {}
            };
            Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['ru-RU','ru','en-US','en'] });
            delete window['__playwright__binding__'];
            delete window['__pw_manual_import__'];
            delete window['__pw_init_script__'];
            console.log('✅ Manual stealth applied');
        """)
        logger.info("✅ Ручная маскировка применена")

    async def random_delay(self, min_sec=0.5, max_sec=2.0):
        await asyncio.sleep(random.uniform(min_sec, max_sec))

    async def human_like_scroll(self, page=None):
        page = page or self.page
        if not page:
            return
        for _ in range(random.randint(2, 5)):
            await page.evaluate(f"""
                window.scrollBy({{ top: {random.randint(200, 600)}, behavior: 'smooth' }});
            """)
            await asyncio.sleep(random.uniform(0.3, 0.8))

    async def wait_for_element(self, selector: str, timeout: int = 30000) -> bool:
        if not self.page:
            return False
        try:
            await self.page.wait_for_selector(selector, timeout=timeout, state='visible')
            return True
        except:
            return False

    async def take_screenshot(self, name: str = "screenshot") -> Optional[str]:
        if not self.page:
            return None
        try:
            os.makedirs('screenshots', exist_ok=True)
            from datetime import datetime
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"screenshots/{name}_{ts}.png"
            await self.page.screenshot(path=filename, full_page=True)
            logger.info(f"📸 Скриншот сохранен: {filename}")
            return filename
        except Exception as e:
            logger.error(f"❌ Ошибка скриншота: {e}")
            return None

    async def extract_price(self, text: str) -> float:
        if not text:
            return 0.0
        cleaned = re.sub(r'[^\d.,]', '', text)
        cleaned = cleaned.replace(',', '.')
        try:
            return float(cleaned)
        except:
            return 0.0

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        try:
            if self.context:
                await self.context.close()
            if self._owns_browser and self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            logger.info("🛑 Браузер закрыт")
        except Exception as e:
            logger.error(f"❌ Ошибка закрытия: {e}")