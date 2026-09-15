# app/api/v1/endpoints/spider.py

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select  # 👈 1. ИМПОРТИРУЕМ select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from typing import Optional, List

from app.core.database import get_db
from app.models.product import Product
from app.models.source import Source
from app.models.history import History
from app.services.spider import Spider
import logging  # 👈 2. ИМПОРТИРУЕМ logging

logger = logging.getLogger(__name__)
router = APIRouter()


class ParseRequest(BaseModel):
    query: str
    user_id: int
    max_sources: Optional[int] = 10  # 👈 может быть None


@router.post("/parse", response_model=dict)
async def parse_product(
    request: ParseRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    # 3. ИСПРАВЛЯЕМ ОШИБКУ С max_sources
    max_sources = request.max_sources or 10  # 👈 если None → 10

    background_tasks.add_task(
        run_spider,
        db=db,
        query=request.query,
        user_id=request.user_id,
        max_sources=max_sources  # 👈 теперь точно int
    )

    return {
        "status": "pending",
        "message": f"Поиск товара '{request.query}' запущен",
        "user_id": request.user_id,
        "max_sources": max_sources
    }


@router.get("/status/{product_id}")
async def get_parse_status(
    product_id: int,
    db: AsyncSession = Depends(get_db)
):
    # 4. ИСПРАВЛЯЕМ ОШИБКУ "select is not defined"
    result = await db.execute(
        select(Product).where(Product.id == product_id)  # 👈 select теперь определён
    )
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # 5. ИСПРАВЛЯЕМ ОШИБКУ "History is not defined"
    history_result = await db.execute(
        select(History).where(History.product_id == product_id)  # 👈 History определён
    )
    history = history_result.scalars().all()

    return {
        "product_id": product_id,
        "query": product.query,
        "status": "completed",
        "history": [
            {
                "event": h.event_type,
                "status": h.status,
                "message": h.message,
                "time": h.created_at
            }
            for h in history
        ]
    }


async def run_spider(
    db: AsyncSession,
    query: str,
    user_id: int,
    max_sources: int
):
    """Фоновая задача для запуска паука."""
    try:
        async with Spider(db) as spider:
            spider.max_sources = max_sources
            await spider.search_product(query, user_id)
    except Exception as e:
        logger.error(f"❌ Ошибка в spider: {e}")  # 👈 logger определён
        raise