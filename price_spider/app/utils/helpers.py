# app/utils/helpers.py
import re
import hashlib
import random
from typing import Optional, Dict, Any
from datetime import datetime, timedelta


def extract_price(text: str) -> Optional[float]:
    """
    Извлечение цены из текста.
    Обрабатывает форматы: "1 299 ₽", "1,299.00", "1299.00"
    """
    if not text:
        return None
    
    # Убираем все символы кроме цифр, точки, запятой и пробелов
    cleaned = re.sub(r'[^\d.,\s]', '', text)
    # Убираем пробелы
    cleaned = re.sub(r'\s', '', cleaned)
    # Меняем запятую на точку
    cleaned = cleaned.replace(',', '.')
    
    # Находим все числа
    numbers = re.findall(r'\d+\.?\d*', cleaned)
    if not numbers:
        return None
    
    # Берем первое число (обычно это и есть цена)
    try:
        return float(numbers[0])
    except:
        return None


def generate_product_hash(product_data: Dict[str, Any]) -> str:
    """
    Генерация уникального хэша для товара.
    """
    # Берем ключевые поля для хэша
    key_fields = [
        product_data.get('product_id', ''),
        product_data.get('product_url', ''),
        str(product_data.get('price', '')),
        product_data.get('title', '')[:50],
    ]
    
    key_string = '|'.join(key_fields)
    return hashlib.md5(key_string.encode()).hexdigest()


def is_price_changed(old_price: float, new_price: float, threshold: float = 0.01) -> bool:
    """
    Проверка изменения цены с порогом чувствительности.
    """
    if old_price is None or new_price is None:
        return True
    
    diff = abs(old_price - new_price)
    return diff > threshold


def calculate_discount(old_price: float, new_price: float) -> Optional[int]:
    """
    Расчет скидки в процентах.
    """
    if not old_price or not new_price or old_price <= 0 or new_price <= 0:
        return None
    
    if new_price >= old_price:
        return 0
    
    discount = ((old_price - new_price) / old_price) * 100
    return round(discount)


def format_currency(amount: float, currency: str = 'RUB') -> str:
    """
    Форматирование цены с валютой.
    """
    if amount is None:
        return ''
    
    symbols = {
        'RUB': '₽',
        'USD': '$',
        'EUR': '€',
        'GBP': '£',
    }
    
    symbol = symbols.get(currency, currency)
    return f"{amount:,.0f} {symbol}".replace(',', ' ')


def random_delay(min_seconds: float = 0.5, max_seconds: float = 2.0) -> float:
    """
    Генерация случайной задержки.
    """
    return random.uniform(min_seconds, max_seconds)


def parse_rating(rating_text: str) -> Optional[float]:
    """
    Парсинг рейтинга из текста.
    """
    if not rating_text:
        return None
    
    # Ищем число с точкой или запятой
    match = re.search(r'(\d+[,.]\d+)', rating_text)
    if match:
        return float(match.group(1).replace(',', '.'))
    
    return None


def parse_reviews_count(text: str) -> Optional[int]:
    """
    Парсинг количества отзывов.
    """
    if not text:
        return None
    
    # Убираем все кроме цифр
    cleaned = re.sub(r'[^\d]', '', text)
    try:
        return int(cleaned)
    except:
        return None


def clean_html(html_text: str) -> str:
    """
    Очистка HTML от тегов.
    """
    if not html_text:
        return ''
    
    # Убираем теги
    cleaned = re.sub(r'<[^>]+>', '', html_text)
    # Убираем лишние пробелы и переносы
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


def truncate_text(text: str, max_length: int = 500) -> str:
    """
    Обрезка текста до указанной длины.
    """
    if not text:
        return ''
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length] + '...'


def safe_get(data: Dict, keys: list, default=None):
    """
    Безопасное получение значения из вложенного словаря.
    """
    for key in keys:
        try:
            data = data[key]
        except (KeyError, TypeError, IndexError):
            return default
    return data


def parse_user_agent(user_agent: str) -> Dict[str, str]:
    """
    Парсинг User-Agent на компоненты.
    """
    result = {
        'browser': 'unknown',
        'browser_version': 'unknown',
        'os': 'unknown',
        'os_version': 'unknown',
        'device': 'desktop',
    }
    
    # Определяем браузер
    if 'Chrome' in user_agent:
        result['browser'] = 'Chrome'
        match = re.search(r'Chrome/(\d+\.\d+)', user_agent)
        if match:
            result['browser_version'] = match.group(1)
    elif 'Firefox' in user_agent:
        result['browser'] = 'Firefox'
        match = re.search(r'Firefox/(\d+\.\d+)', user_agent)
        if match:
            result['browser_version'] = match.group(1)
    elif 'Safari' in user_agent and 'Chrome' not in user_agent:
        result['browser'] = 'Safari'
        match = re.search(r'Version/(\d+\.\d+)', user_agent)
        if match:
            result['browser_version'] = match.group(1)
    
    # Определяем ОС
    if 'Windows' in user_agent:
        result['os'] = 'Windows'
        if 'Windows NT 10.0' in user_agent:
            result['os_version'] = '10'
        elif 'Windows NT 6.1' in user_agent:
            result['os_version'] = '7'
    elif 'Mac OS X' in user_agent:
        result['os'] = 'macOS'
    elif 'Linux' in user_agent:
        result['os'] = 'Linux'
    elif 'Android' in user_agent:
        result['os'] = 'Android'
        result['device'] = 'mobile'
    elif 'iPhone' in user_agent or 'iPad' in user_agent:
        result['os'] = 'iOS'
        result['device'] = 'mobile'
    
    return result