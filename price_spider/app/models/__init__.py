# app/models/__init__.py
from app.models.product import Product
from app.models.source import Source
from app.models.history import History

# Экспортируем для Alembic и других модулей
__all__ = ["Product", "Source", "History"]
