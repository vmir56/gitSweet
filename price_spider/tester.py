import os
from playwright.sync_api import sync_playwright
# Импортируем новый класс Stealth вместо старой функции
from playwright_stealth import Stealth

USER_DATA_DIR = os.path.expanduser("/Users/v.ant/mk/vs/price_spider/chrome_profile")

# Инициализируем Stealth через его новый метод use_sync
with Stealth().use_sync(sync_playwright()) as p:
    # Запускаем Chromium с сохранением профиля
    context = p.chromium.launch_persistent_context(
        user_data_dir=USER_DATA_DIR,
        headless=False,
        # Подменяем User-Agent на актуальный человеческий
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        ignore_default_args=["--enable-automation"],
        args=[
            "--disable-blink-features=AutomationControlled",
            "--start-maximized"
        ]
    )
    
    # Теперь маскировка применяется АВТОМАТИЧЕСКИ ко всем страницам!
    # Строчка stealth_sync(page) больше не нужна.
    page = context.pages[0]
    
    page.goto("https://ya.ru")
    # page.goto("https://ozon.ru")

    
    print("Браузер успешно замаскирован новым методом.")
    input("Авторизуйтесь на Ozon и нажмите ENTER в терминале для завершения...")
