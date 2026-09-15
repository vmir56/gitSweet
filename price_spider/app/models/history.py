# app/models/history.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base



class History(Base):
    __tablename__ = "history"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    source_id = Column(Integer, ForeignKey("sources.id", ondelete="CASCADE"), nullable=True)
    
    # Что произошло
    event_type = Column(String(50), nullable=False)  # 'search', 'parse', 'price_change', 'error'
    status = Column(String(20), default="success")  # 'success', 'error', 'warning'
    message = Column(Text, nullable=True)
    
    # Данные снапшота (что было до/после)
    snapshot = Column(JSON, nullable=True)  # {"price": 1000, "availability": true}
    
    # Технические метаданные
    ip_used = Column(String(45), nullable=True)
    proxy_used = Column(String(100), nullable=True)
    duration_ms = Column(Integer, nullable=True)  # Время выполнения
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Связи
    product = relationship("Product", back_populates="history")
    source = relationship("Source", back_populates="history")