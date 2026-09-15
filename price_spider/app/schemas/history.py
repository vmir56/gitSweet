# app/schemas/history.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class EventType(str, Enum):
    """Типы событий"""
    SEARCH = "search"
    PARSE = "parse"
    PRICE_CHANGE = "price_change"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class HistoryBase(BaseModel):
    """Базовый класс для истории"""
    product_id: int = Field(..., description="ID товара")
    source_id: Optional[int] = Field(None, description="ID источника (если применимо)")
    event_type: str = Field(..., description="Тип события")
    status: str = Field("success", description="Статус: success/error/warning/pending")
    message: Optional[str] = Field(None, description="Сообщение")
    snapshot: Optional[Dict[str, Any]] = Field(None, description="Снапшот данных")
    ip_used: Optional[str] = Field(None, max_length=45, description="Использованный IP")
    proxy_used: Optional[str] = Field(None, max_length=100, description="Использованный прокси")
    duration_ms: Optional[int] = Field(None, description="Длительность в миллисекундах")


class HistoryCreate(HistoryBase):
    """Создание записи истории"""
    pass


class HistoryResponse(HistoryBase):
    """Ответ с данными истории"""
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "product_id": 1,
                "source_id": 1,
                "event_type": "parse",
                "status": "success",
                "message": "Товар успешно спарсен",
                "snapshot": {"price": 99999.0, "availability": True},
                "ip_used": "192.168.1.1",
                "proxy_used": "http://proxy1:8080",
                "duration_ms": 1500,
                "created_at": "2024-01-01T12:00:00"
            }
        }