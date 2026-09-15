from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session, joinedload
from typing import List
from .. import models, schemas, database

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

router = APIRouter()

# Получаем сессию базы данных как зависимость
async def get_db():
    async with database.AsyncSessionLocal() as db:
        yield db

# Создание заказа
@router.post("/", response_model=schemas.OrderResponse)
async def create_order(order: schemas.OrderCreate, db: AsyncSession = Depends(get_db)):
    db_order = models.Order(user_id=order.user_id, total_price=0)  # Сначала создаём заказ без товаров
    db.add(db_order)
    await db.commit()
    await db.refresh(db_order)
    
    # Добавляем товары в заказ
    total_price = 0
    for product_id in order.product_ids:
        stmt = select(models.Product).filter(models.Product.id == product_id)
        result = await db.execute(stmt)
        product = result.scalars().first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product with id {product_id} not found")
        
        order_item = models.OrderItem(order_id=db_order.id, product_id=product.id, quantity=1)
        db.add(order_item)
        total_price += product.price
    
    db_order.total_price = total_price
    await db.commit()
    await db.refresh(db_order)
    
    return db_order

# Получение всех заказов с товарами
@router.get("/", response_model=List[schemas.OrderResponse])
async def read_orders(db: AsyncSession = Depends(get_db)):
    stmt = select(models.Order).options(joinedload(models.Order.items).joinedload(models.OrderItem.product))
    result = await db.execute(stmt)
    db_orders = result.scalars().all()
    return db_orders

# Получение заказа по ID с товарами
@router.get("/{order_id}", response_model=schemas.OrderResponse)
async def read_order(order_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(models.Order).options(joinedload(models.Order.items).joinedload(models.OrderItem.product)).filter(models.Order.id == order_id)
    result = await db.execute(stmt)
    db_order = result.scalars().first()
    if db_order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return db_order

# Удаление заказа
@router.delete("/{order_id}", response_model=schemas.OrderResponse)
async def delete_order(order_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(models.Order).filter(models.Order.id == order_id)
    result = await db.execute(stmt)
    db_order = result.scalars().first()
    if db_order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    
    await db.delete(db_order)
    await db.commit()
    
    return db_order
