# app/api/v1/endpoints/ozon.py
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from app.core.database import get_db
from app.models.product import Product
from app.models.source import Source
from app.models.history import History
from app.services.parsers.ozon_parser import OzonParser
from app.api.v1.endpoints import validate_api_key  # 👈 ИМПОРТ ЗАЩИТЫ

router = APIRouter()

class SearchRequest(BaseModel):
    query: str
    user_id: Optional[int] = 1  # позже будет из авторизации
    max_results: int = 5

@router.post("/ozon/search")
async def search_ozon(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db),
    _ = Depends(validate_api_key)  # 👈 ЗАЩИТА ЭНДПОИНТА
):
    async with OzonParser(headless=True) as parser:
        try:
            # 1. Парсим товары
            items = await parser.search_product(request.query)
            if not items:
                return {
                    "status": "success",
                    "query": request.query,
                    "total": 0,
                    "results": []
                }

            # 2. Ограничиваем количество
            items = items[:request.max_results]

            # 3. Создаём запись о продукте
            product = Product(
                user_id=request.user_id,
                query=request.query,
                name=items[0].get("title", request.query)[:500] if items else request.query
            )
            db.add(product)
            await db.flush()  # получаем product.id

            # 4. Сохраняем источники (sources)
            for item in items:
                source = Source(
                    product_id=product.id,
                    shop_name="Ozon",
                    shop_url="https://www.ozon.ru",
                    product_url=item.get("url", ""),
                    price=item.get("price"),
                    old_price=item.get("old_price"),
                    currency="RUB",
                    availability=True,
                    stock_count=None,
                    raw_data=item
                )
                db.add(source)

            # 5. Логируем действие (history)
            history = History(
                product_id=product.id,
                event_type="search",
                status="success",
                message=f"Найдено {len(items)} товаров по запросу '{request.query}'",
                snapshot={"query": request.query, "count": len(items)}
            )
            db.add(history)

            # 6. Сохраняем всё в БД
            await db.commit()

            # 7. Возвращаем результат
            return {
                "status": "success",
                "query": request.query,
                "total": len(items),
                "product_id": product.id,
                "results": items
            }

        except Exception as e:
            # Логируем ошибку в history
            try:
                error_history = History(
                    product_id=None,
                    event_type="error",
                    status="error",
                    message=f"Ошибка при поиске '{request.query}': {str(e)}",
                    snapshot={"query": request.query}
                )
                db.add(error_history)
                await db.commit()
            except:
                pass
            raise HTTPException(status_code=500, detail=str(e))