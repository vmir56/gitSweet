# app/models/product.py
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)  # Кто запросил
    query = Column(String(500), nullable=False)  # Поисковый запрос
    name = Column(String(500), nullable=True)  # Нормализованное имя
    brand = Column(String(200), nullable=True)
    model = Column(String(200), nullable=True)
    ean = Column(String(13), nullable=True, index=True)  # Штрихкод
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    sources = relationship("Source", back_populates="product", cascade="all, delete-orphan")
    history = relationship("History", back_populates="product", cascade="all, delete-orphan")