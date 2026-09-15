# app/schemas/source.py
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, Dict, Any
from datetime import datetime


class SourceBase(BaseModel):
    """Базовый класс для источника данных"""
    product_id: int = Field(..., description="ID товара")
    shop_name: str = Field(..., max_length=200, description="Название магазина")
    shop_url: str = Field(..., max_length=500, description="URL магазина")
    product_url: str = Field(..., max_length=500, description="URL товара")
    price: Optional[float] = Field(None, description="Текущая цена")
    old_price: Optional[float] = Field(None, description="Старая цена (со скидкой)")
    currency: str = Field("RUB", max_length=3, description="Валюта")
    availability: bool = Field(True, description="В наличии?")
    stock_count: Optional[int] = Field(None, description="Количество на складе")
    raw_data: Optional[Dict[str, Any]] = Field(None, description="Сырые данные парсинга")
    screenshot: Optional[str] = Field(None, max_length=500, description="Ссылка на скриншот")


class SourceCreate(SourceBase):
    """Создание источника"""
    pass


class SourceUpdate(BaseModel):
    """Обновление источника"""
    price: Optional[float] = None
    old_price: Optional[float] = None
    availability: Optional[bool] = None
    stock_count: Optional[int] = None
    is_active: Optional[bool] = None


class SourceResponse(SourceBase):
    """Ответ с данными источника"""
    id: int
    parsed_at: datetime
    is_active: bool
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "product_id": 1,
                "shop_name": "Ozon",
                "shop_url": "https://www.ozon.ru",
                "product_url": "https://www.ozon.ru/product/12345",
                "price": 99999.0,
                "old_price": 119999.0,
                "currency": "RUB",
                "availability": True,
                "stock_count": 10,
                "parsed_at": "2024-01-01T12:00:00",
                "is_active": True
            }
        }