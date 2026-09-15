# app/schemas/product.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ProductBase(BaseModel):
    """Базовый класс для товара"""
    user_id: int = Field(..., description="ID пользователя, запросившего товар")
    query: str = Field(..., max_length=500, description="Поисковый запрос")
    name: Optional[str] = Field(None, max_length=500, description="Нормализованное название")
    brand: Optional[str] = Field(None, max_length=200, description="Бренд")
    model: Optional[str] = Field(None, max_length=200, description="Модель")
    ean: Optional[str] = Field(None, max_length=13, description="Штрихкод EAN-13")


class ProductCreate(ProductBase):
    """Создание товара"""
    pass


class ProductUpdate(BaseModel):
    """Обновление товара"""
    name: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    ean: Optional[str] = None


class ProductResponse(ProductBase):
    """Ответ с данными товара"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "user_id": 100,
                "query": "iPhone 15 Pro",
                "name": "iPhone 15 Pro 256GB",
                "brand": "Apple",
                "model": "iPhone 15 Pro",
                "ean": "1234567890123",
                "created_at": "2024-01-01T12:00:00",
                "updated_at": "2024-01-01T12:00:00"
            }
        }