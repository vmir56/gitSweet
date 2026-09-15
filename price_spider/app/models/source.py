# app/models/source.py
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Source(Base):
    __tablename__ = "sources"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    
    # Данные источника
    shop_name = Column(String(200), nullable=False)
    shop_url = Column(String(500), nullable=False)
    product_url = Column(String(500), nullable=False)
    price = Column(Float, nullable=True)
    old_price = Column(Float, nullable=True)
    currency = Column(String(3), default="RUB")
    availability = Column(Boolean, default=True)  # В наличии?
    stock_count = Column(Integer, nullable=True)  # Если указано
    
    # Сырые данные
    raw_data = Column(JSON, nullable=True)  # Полный JSON ответа
    screenshot = Column(String(500), nullable=True)  # Ссылка на скриншот (опционально)
    
    # Метаданные парсинга
    parsed_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)
    
    # Связи
    product = relationship("Product", back_populates="sources")
    history = relationship("History", back_populates="source")