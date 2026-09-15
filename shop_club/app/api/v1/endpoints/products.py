# shop_club/app/api/v1/endpoints/products.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from app.services.spider_client import SpiderClient, get_spider_client
from app.api.v1.endpoints.auth import get_current_user  # есть авторизация?

router = APIRouter()


class SearchRequest(BaseModel):
    query: str
    max_results: int = 5


@router.post("/products/search")
async def search_prices(
    request: SearchRequest,
    current_user = Depends(get_current_user),  # 👈 АВТОРИЗАЦИЯ В SHOP_CLUB
    spider: SpiderClient = Depends(get_spider_client)
):
    """
    Поиск цен на товар через микросервис price_spider.
    Доступно только авторизованным пользователям.
    """
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
            "results": result.get("results", []),
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Price Spider unavailable: {str(e)}"
        )


@router.get("/products/{product_id}/prices")
async def get_product_prices(
    product_id: int,
    current_user = Depends(get_current_user),
    spider: SpiderClient = Depends(get_spider_client)
):
    """
    Получение сохранённых цен для товара из price_spider.
    """
    try:
        status = await spider.get_parse_status(product_id)
        return status
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/spider/health")
async def check_spider_health(
    spider: SpiderClient = Depends(get_spider_client)
):
    """Проверка доступности микросервиса парсинга"""
    is_healthy = await spider.health_check()
    return {
        "service": "price_spider",
        "status": "healthy" if is_healthy else "unavailable",
        "url": spider.base_url
    }