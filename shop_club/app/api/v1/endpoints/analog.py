# shop_club/app/api/v1/endpoints/analog.py

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
#import requests
from urllib.parse import urlparse

from app.database import get_db
from app.models import Product, User, Category
from app.schemas import AnalogCreate
from app.auth import get_current_user

from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker

router = APIRouter()

class SaveAnalogRequest(BaseModel):
    name: str
    price: float
    old_price: Optional[float] = None
    image_url: Optional[str] = None
    source: str = "ozon"
    source_url: Optional[str] = None
    analog_query: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[int] = None


def download_image(url: str, product_id: int) -> Optional[str]:
    """Скачивает изображение и сохраняет локально"""
    try:
        # Проверяем, что URL корректный
        if not url or not url.startswith(('http://', 'https://')):
            return None
        
        # Получаем расширение файла
        parsed_url = urlparse(url)
        path = parsed_url.path
        ext = path.split('.')[-1] if '.' in path else 'jpg'
        if ext.lower() not in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
            ext = 'jpg'
        
        # Скачиваем изображение
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return None
        
        # Сохраняем в папку static/uploads
        import os
        from datetime import datetime
        
        upload_dir = 'app/static/uploads'
        os.makedirs(upload_dir, exist_ok=True)
        
        filename = f"analog_{product_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
        filepath = os.path.join(upload_dir, filename)
        
        with open(filepath, 'wb') as f:
            f.write(response.content)
        
        return f"/static/uploads/{filename}"
        
    except Exception as e:
        print(f"⚠️ Ошибка загрузки изображения: {e}")
        return None


@router.post("/analog/save")
async def save_analog(
    data: SaveAnalogRequest,
    request: Request,  #ДОБАВИЛ
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Сохраняет найденный аналог в основную таблицу products с флагом is_analog=True
    """
     # 👇 ВРЕМЕННО ЛОГИРУЕМ
    print(f"🔍 Токен из заголовка: {request.headers.get('Authorization')}")
    print(f"🔍 Токен из куки: {request.cookies.get('access_token')}")
    print(f"🔍 Пользователь: {current_user}")



    print(f"🔍 Куки: {request.cookies}")
    print(f"🔍 Заголовки: {request.headers.get('Authorization')}")

    
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    ######   
    # Проверяем, не существует ли уже такой аналог (по source_url)
    if data.source_url:
        stmt_existing = select(Product).filter(
            Product.source_url == data.source_url,
            Product.is_analog == True
        )
        result_existing = await db.execute(stmt_existing)
        existing = result_existing.scalars().first()
        if existing:
            raise HTTPException(status_code=400, detail="Этот аналог уже сохранён")
    
    # Если есть категория — проверяем её существование
    category_id = data.category_id
    if category_id:
        stmt_category = select(Category).filter(Category.id == category_id)
        result_category = await db.execute(stmt_category)
        category = result_category.scalars().first()
        if not category:
            category_id = None

    # Создаём товар как аналог
    analog = Product(
        user_id=current_user.id,
        name=data.name,
        description=data.description,
        price=data.price,
        old_price=data.old_price,
        stock=0,  # У аналогов нет своего склада
        image_url=data.image_url,  # Пока сохраняем оригинальный URL
        category_id=category_id,
        is_analog=True,
        source=data.source,
        source_url=data.source_url,
        analog_query=data.analog_query,
        created_at=datetime.utcnow()
    )
    
    db.add(analog)
    await db.commit()
    await db.refresh(analog)
    
    # Пробуем скачать изображение (в фоне)
    if data.image_url:
        local_image = download_image(data.image_url, analog.id)
        if local_image:
            analog.image_url = local_image
            await db.commit()
    
    return {
        "status": "success",
        "message": "Аналог сохранён",
        "product": {
            "id": analog.id,
            "name": analog.name,
            "price": analog.price,
            "old_price": analog.old_price,
            "image_url": analog.image_url,
            "source": analog.source,
            "source_url": analog.source_url,
            "is_analog": analog.is_analog
        }
    }

    # Нужно добавить связь пользователь-аналог
    # Для упрощения — возвращаем все аналоги (позже добавим user_id в Product)
@router.get("/analog/my")
async def get_my_analogs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Возвращает все сохранённые аналоги текущего пользователя"""
    # Предполагается, что у модели Product есть поле user_id для связи с пользователем
    stmt = select(Product).filter(
        Product.is_analog == True,
        Product.user_id == current_user.id  # Предполагается, что у Product есть поле user_id
    )
    result = await db.execute(stmt)
    analogs = result.scalars().all()
    return analogs

@router.delete("/analog/{analog_id}")
async def delete_analog(
    analog_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Удаляет сохранённый аналог"""
    stmt = select(Product).filter(
        Product.id == analog_id,
        Product.is_analog == True
    )
    result = await db.execute(stmt)
    analog = result.scalars().first()    
    if not analog:
        raise HTTPException(status_code=404, detail="Аналог не найден")
    
    await db.delete(analog)
    await db.commit()
    
    return {"status": "success", "message": "Аналог удалён"}