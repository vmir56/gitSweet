# app/routes/products.py
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from typing import List

from .. import models, schemas, database
from ..database import AsyncSessionLocal #, get_db

router = APIRouter()

# ========== ПОЛУЧЕНИЕ СЕССИИ (async) ==========
async def get_async_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# ========== СОЗДАНИЕ ТОВАРА ==========
@router.post("/", response_model=schemas.ProductResponse)
async def create_product(
    product: schemas.ProductCreate,
    db: AsyncSession = Depends(get_async_db)
):
    db_product = models.Product(**product.dict())
    db.add(db_product)
    await db.commit()
    await db.refresh(db_product)
    return db_product

# ========== ПОЛУЧЕНИЕ ВСЕХ ТОВАРОВ ==========
@router.get("/", response_model=List[schemas.ProductResponse])
async def read_products(db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(models.Product))
    return result.scalars().all()

# ========== ПОЛУЧЕНИЕ ТОВАРА ПО ID ==========
@router.get("/{product_id}", response_model=schemas.ProductResponse)
async def read_product(product_id: int, db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(
        select(models.Product).where(models.Product.id == product_id)
    )
    db_product = result.scalar_one_or_none()
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return db_product

# ========== ОБНОВЛЕНИЕ ТОВАРА ==========
@router.put("/{product_id}", response_model=schemas.ProductResponse)
async def update_product(
    product_id: int,
    product: schemas.ProductCreate,
    db: AsyncSession = Depends(get_async_db)
):
    result = await db.execute(
        select(models.Product).where(models.Product.id == product_id)
    )
    db_product = result.scalar_one_or_none()
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    
    db_product.name = product.name
    db_product.description = product.description
    db_product.price = product.price
    db_product.category_id = product.category_id

    await db.commit()
    await db.refresh(db_product)
    return db_product

# ========== УДАЛЕНИЕ ТОВАРА ==========
@router.delete("/{product_id}", response_model=schemas.ProductResponse)
async def delete_product(product_id: int, db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(
        select(models.Product).where(models.Product.id == product_id)
    )
    db_product = result.scalar_one_or_none()
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    await db.delete(db_product)
    await db.commit()
    return db_product