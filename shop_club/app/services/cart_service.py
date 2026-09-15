import uuid
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from fastapi import Request, Response
from .. import models

from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

class CartService:

    @staticmethod
    async def sync_guest_cart_to_user(
        db: AsyncSession,
        session_id: str,
        user_id: int
    ):
        """Перенести корзину гостя в аккаунт пользователя после логина"""
        # Находим все товары гостя
        stmt = select(models.CartItem).filter(
            models.CartItem.session_id == session_id
        )
        result = await db.execute(stmt)
        guest_items = result.scalars().all()
        
        for guest_item in guest_items:
            # Ищем такой же товар у пользователя
            user_item_stmt = select(models.CartItem).filter(
                models.CartItem.user_id == user_id,
                models.CartItem.product_id == guest_item.product_id
            )
            user_item_result = await db.execute(user_item_stmt)
            user_item = user_item_result.scalars().first()
            
            if user_item:
                # Объединяем количество
                user_item.quantity += guest_item.quantity
                user_item.updated_at = datetime.utcnow()
                await db.delete(guest_item)
            else:
                # Переносим товар пользователю
                guest_item.user_id = user_id
                guest_item.session_id = None
                guest_item.updated_at = datetime.utcnow()
        
        await db.commit()

    @staticmethod
    async def get_cart(
        db: AsyncSession,
        user_id: Optional[int] = None,
        session_id: Optional[str] = None
    ) -> Dict:
        """Получить корзину для пользователя или гостя"""
        stmt = (
            select(models.CartItem, models.Product)
            .join(models.Product, models.CartItem.product_id == models.Product.id)
        )
        
        if user_id:
            stmt = stmt.filter(models.CartItem.user_id == user_id)
        elif session_id:
            stmt = stmt.filter(models.CartItem.session_id == session_id)
        else:
            return {"items": [], "total": 0, "count": 0}
        
        result = await db.execute(stmt)
        results = []
        total = 0
        count = 0
        
        for cart_item, product in result:
            item_total = product.price * cart_item.quantity
            total += item_total
            count += cart_item.quantity
            results.append({
                "id": cart_item.id,
                "product_id": product.id,
                "name": product.name,
                "price": product.price,
                "quantity": cart_item.quantity,
                "total": item_total,
                "image": getattr(product, 'image', None)
            })
        
        return {"items": results, "total": total, "count": count}
         
    @staticmethod
    async def add_item(
        db: AsyncSession,
        product_id: int,
        quantity: int = 1,
        user_id: Optional[int] = None,
        session_id: Optional[str] = None
    ) -> models.CartItem:
        """Добавить товар в корзину"""
        if not user_id and not session_id:
            raise ValueError("Either user_id or session_id must be provided")
        
        # Находим существующий товар в корзине
        stmt = (
            select(models.CartItem)
            .filter(models.CartItem.product_id == product_id)
        )
        
        if user_id:
            stmt = stmt.filter(models.CartItem.user_id == user_id)
        elif session_id:
            stmt = stmt.filter(models.CartItem.session_id == session_id)
        
        result = await db.execute(stmt)
        cart_item = result.scalars().first()
        
        if cart_item:
            cart_item.quantity += quantity
            cart_item.updated_at = datetime.utcnow()
        else:
            cart_item = models.CartItem(
                user_id=user_id,
                session_id=session_id,
                product_id=product_id,
                quantity=quantity
            )
            db.add(cart_item)
        
        await db.commit()
        await db.refresh(cart_item)
        return cart_item
 
    @staticmethod
    async def update_quantity(
        db: AsyncSession,
        item_id: int,
        quantity: int,
        user_id: Optional[int] = None,
        session_id: Optional[str] = None
    ) -> Optional[models.CartItem]:
        """Обновить количество товара"""
        stmt = select(models.CartItem).filter(models.CartItem.id == item_id)
        if user_id:
            stmt = stmt.filter(models.CartItem.user_id == user_id)
        elif session_id:
            stmt = stmt.filter(models.CartItem.session_id == session_id)
        
        result = await db.execute(stmt)
        cart_item = result.scalars().first()
        
        if not cart_item:
            return None
        
        if quantity <= 0:
            await db.delete(cart_item)
            await db.commit()
            return None
        else:
            cart_item.quantity = quantity
            cart_item.updated_at = datetime.utcnow()
            await db.commit()
            await db.refresh(cart_item)
            return cart_item

    @staticmethod
    async def remove_item(
        db: AsyncSession,
        item_id: int,
        user_id: Optional[int] = None,
        session_id: Optional[str] = None
    ) -> bool:
        """Удалить товар из корзины"""
        stmt = select(models.CartItem).filter(models.CartItem.id == item_id)
        if user_id:
            stmt = stmt.filter(models.CartItem.user_id == user_id)
        elif session_id:
            stmt = stmt.filter(models.CartItem.session_id == session_id)
        
        result = await db.execute(stmt)
        cart_item = result.scalars().first()
        
        if not cart_item:
            return False
        
        await db.delete(cart_item)
        await db.commit()
        return True

    @staticmethod
    async def clear_cart(
        db: AsyncSession,
        user_id: Optional[int] = None,
        session_id: Optional[str] = None
    ):
        """Очистить всю корзину"""
        stmt = select(models.CartItem)
        if user_id:
            stmt = stmt.filter(models.CartItem.user_id == user_id)
        elif session_id:
            stmt = stmt.filter(models.CartItem.session_id == session_id)
        
        result = await db.execute(stmt)
        cart_items = result.scalars().all()
        
        for cart_item in cart_items:
            await db.delete(cart_item)
        
        await db.commit()