# shop_club/app/api/v1/endpoints/spider.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services.spider_client import SpiderClient, get_spider_client
from app.auth import get_current_user  # 👈 ИМПОРТИРУЕМ АВТОРИЗАЦИЮ ИЗ app.auth
from app.models import User

router = APIRouter()


class SearchRequest(BaseModel):
    query: str
    max_results: int = 5


@router.post("/spider/search")
async def search_prices(
    request: SearchRequest,
    current_user: User = Depends(get_current_user),  # 👈 ЗАЩИТА ЭНДПОИНТА
    spider: SpiderClient = Depends(get_spider_client)
):
    """Поиск цен через price_spider. Только для авторизованных пользователей."""
    try:
        result = await spider.search_product(
            query=request.query,
            max_results=request.max_results,
            user_id=current_user.id
        )
        return {
            "status": "success",
            "user": current_user.email,
            "query": request.query,
            "total": result.get("total", 0),
            "results": result.get("results", [])
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Price Spider unavailable: {str(e)}")