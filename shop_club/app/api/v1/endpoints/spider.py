# shop_club/app/api/v1/endpoints/spider.py
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel  # 👈 ДОБАВЬ ЭТУ СТРОЧКУ
from typing import Optional, List

from app.services.spider_client import SpiderClient, get_spider_client
from app.database import get_db
from app.auth import decode_token
from app.models import User

from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal

from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker

router = APIRouter()

class SearchRequest(BaseModel):
    query: str
    max_results: int = 5


@router.post("/spider/search")
async def search_prices(
    request: SearchRequest,
    req: Request,  # 👈 ДОБАВЛЯЕМ Request ДЛЯ КУК
    db: AsyncSession = Depends(get_db),
    spider: SpiderClient = Depends(get_spider_client)
):
    # 👇 ПОЛУЧАЕМ ТОКЕН ИЗ КУК
    token = req.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # 👇 ДЕКОДИРУЕМ ТОКЕН И ПОЛУЧАЕМ ПОЛЬЗОВАТЕЛЯ
    from app.auth import decode_token
    current_user = await decode_token(token, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
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