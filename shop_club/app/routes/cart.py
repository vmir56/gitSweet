from fastapi import APIRouter, Depends, Request, Response, HTTPException, Form
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, selectinload
from typing import Optional
from collections import Counter
import json

from ..database import get_db
from .. import models, auth

from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker

print("=" * 60)
print("CART.PY IS LOADED - routes are registered")
print("=" * 60)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
async def view_cart(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """Просмотр корзины"""
    print("=" * 50)
    print("VIEW_CART called")
    
    current_user = await auth.get_current_user_optional(request, db=db)
    print(f"Current user: {current_user.username if current_user else 'None'}")
    
    if current_user:
        print("=== AUTHORIZED USER ===") 
        #stmt = select(models.CartItem).filter(models.CartItem.user_id == current_user.id)
        stmt = select(models.CartItem).where(models.CartItem.user_id == current_user.id).options(selectinload(models.CartItem.product))
        result = await db.execute(stmt)
        cart_items = result.scalars().all()
        print(f"Found {len(cart_items)} items in DB")
        
        cart_data = []
        total = 0
        for item in cart_items:
            product = item.product
            if product:
                item_total = product.price * item.quantity
                total += item_total
                cart_data.append({
                    "product_id": product.id,
                    "name": product.name,
                    "price": product.price,
                    "quantity": item.quantity,
                    "total": item_total
                })
                print(f"  - {product.name}: {item.quantity} x {product.price} = {item_total}")
        
        cart_count = sum(i.quantity for i in cart_items)
        
        return templates.TemplateResponse(
            request=request,
            name="cart.html",
            context={
                "cart_items": cart_data,
                "total": total,
                "cart_count": cart_count,
                "is_authenticated": True,
                "current_user": current_user
            }
        )
    
    else:
        print("=== GUEST USER ===")
        product_ids = get_cart_from_cookie(request)
        print(f"Product IDs from cookie: {product_ids}")
        print(f"Length: {len(product_ids)}")
        
        if not product_ids:
            print("No products in cookie")
            cart_data = []
            total = 0
            cart_count = 0
        else:
            from collections import Counter
            counts = Counter(product_ids)
            print(f"Counts: {dict(counts)}")
            
            cart_data = []
            total = 0
            
            for product_id, quantity in counts.items():
                print(f"Processing product_id: {product_id}, quantity: {quantity}")          
                stmt = select(models.Product).filter(models.Product.id == product_id)
                result = await db.execute(stmt)
                product = result.scalars().first()
                if product:
                    item_total = product.price * quantity
                    total += item_total
                    cart_data.append({
                        "product_id": product.id,
                        "name": product.name,
                        "price": product.price,
                        "quantity": quantity,
                        "total": item_total
                    })
                    print(f"  + {product.name}: {quantity} x {product.price} = {item_total}")
                else:
                    print(f"  ! Product {product_id} NOT FOUND in database!")
            
            cart_count = len(product_ids)
        
        print(f"Final cart_data length: {len(cart_data)}")
        print(f"Final total: {total}")
        print(f"Final cart_count: {cart_count}")
        
        # Проверяем что передаем в шаблон
        context = {
            "cart_items": cart_data,
            "total": total,
            "cart_count": cart_count,
            "is_authenticated": False,
            "current_user": None
        }
        print(f"Context keys: {context.keys()}")
        print(f"cart_items in context: {len(context['cart_items'])}")
        
        return templates.TemplateResponse(
            request=request,
            name="cart.html",
            context=context
        )
    
def get_cart_from_cookie(request: Request) -> list:
    """Получить список ID товаров из cookie (работает с разными форматами)"""
    cart_cookie = request.cookies.get("cart", "")
    print(f"Raw cookie: '{cart_cookie}'")  # Отладка
    
    if not cart_cookie:
        return []
    
    # Убираем возможные кавычки в начале и конце
    if cart_cookie.startswith('"') and cart_cookie.endswith('"'):
        cart_cookie = cart_cookie[1:-1]
    
    # Заменяем экранированные запятые \054 на обычные
    cart_cookie = cart_cookie.replace('\\054', ',')
    
    # Разбиваем и фильтруем
    product_ids = []
    for part in cart_cookie.split(','):
        part = part.strip()
        if part and part.isdigit():
            product_ids.append(int(part))
        elif part:
            # Если встретили не число, пробуем извлечь цифры
            import re
            numbers = re.findall(r'\d+', part)
            for num in numbers:
                if num:
                    product_ids.append(int(num))
    
    print(f"Parsed product_ids: {product_ids}")  # Отладка
    return product_ids

@router.get("/count")
async def get_cart_count(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Получить количество товаров в корзине"""
    current_user = await auth.get_current_user_optional(request, db=db)
    if current_user:
        stmt = select(models.CartItem).where(models.CartItem.user_id == current_user.id)
        result = await db.execute(stmt)
        items = result.scalars().all()
        cart_count = sum(i.quantity for i in items)
    else:
        product_ids = get_cart_from_cookie(request)
        cart_count = len(product_ids)
    return JSONResponse({"count": cart_count})

@router.post("/add/{product_id}")
async def add_to_cart(
    product_id: int,
    quantity: int = Form(1),
    request: Request = None,
    response: Response = None,
    db: AsyncSession = Depends(get_db)
):
    """Добавить товар в корзину"""
    print(f"=== ADD TO CART: product_id={product_id}, quantity={quantity} ===")
    
    current_user = await auth.get_current_user_optional(request, db=db)
    print(f"User: {current_user.username if current_user else 'None'}")    
    stmt = select(models.Product).filter(models.Product.id == product_id)
    result = await db.execute(stmt)
    product = result.scalars().first()
    if not product:
        return JSONResponse({"success": False, "message": "Product not found"}, status_code=404)
    
    if current_user:
        # Авторизованный - в БД
        print(f"Adding to DB for user {current_user.id}") 
        stmt = select(models.CartItem).filter(
            models.CartItem.user_id == current_user.id,
            models.CartItem.product_id == product_id)
        result = await db.execute(stmt)
        cart_item = result.scalars().first()      
        if cart_item:
            cart_item.quantity += quantity
            print(f"Updated existing: quantity now {cart_item.quantity}")
        else:
            cart_item = models.CartItem(
                user_id=current_user.id,
                product_id=product_id,
                quantity=quantity
            )
            db.add(cart_item)
            print(f"Created new item with quantity {quantity}")
        
        await db.commit()
        
        # Подсчитываем общее количество
        stmt = select(models.CartItem).filter(
        models.CartItem.user_id == current_user.id)
        result = await db.execute(stmt)
        items = result.scalars().all()      
        cart_count = sum(i.quantity for i in items)
        print(f"Total cart count: {cart_count}")
        
        # Для AJAX запросов (из каталога)
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JSONResponse({
                "success": True,
                "cart_count": cart_count,
                "message": f"{product.name} добавлен в корзину"
            })
        
        # Для обычных POST (если форма без JS)
        return RedirectResponse(url=request.headers.get("referer", "/"), status_code=303)
    else:
        # Гость - в cookie
        print(f"Adding to cookie for guest")
        product_ids = get_cart_from_cookie(request)
        
        # Добавляем товар
        for _ in range(quantity):
            product_ids.append(product_id)
        
        # Сохраняем в cookie
        cart_value = ",".join(map(str, product_ids))
        cart_count = len(product_ids)
        
        print(f"New cookie value: {cart_value[:50]}...")
        print(f"Cart count: {cart_count}")
        
        json_response = JSONResponse({
            "success": True,
            "cart_count": cart_count,
            "message": f"{product.name} добавлен в корзину"
        })
        
        json_response.set_cookie(
            key="cart",
            value=cart_value,
            max_age=30*24*60*60,
            path="/",
            samesite="lax",
            secure=False,
            httponly=False
        )
        
        return json_response 
###

@router.get("/debug-full")
async def debug_full(request: Request, db: AsyncSession = Depends(get_db)):
    """Полная отладка корзины"""
    product_ids = get_cart_from_cookie(request)
    from collections import Counter
    counts = Counter(product_ids)
    
    products_info = []
    for pid, qty in counts.items():     
        stmt = select(models.Product).filter(models.Product.id == pid)
        result = await db.execute(stmt)
        product = result.scalars().first()
        products_info.append({
            "product_id": pid,
            "name": product.name if product else "NOT FOUND",
            "price": product.price if product else 0,
            "quantity": qty,
            "total": (product.price * qty) if product else 0
        })
    
    return {
        "raw_cookie": request.cookies.get("cart", ""),
        "product_ids": product_ids,
        "counts": dict(counts),
        "products_info": products_info,
        "total": sum(p["total"] for p in products_info)
    }

@router.post("/update/{product_id}")
async def update_cart_item(
    product_id: int,
    quantity: int = Form(...),
    request: Request = None,
    response: Response = None,
    db: Session = Depends(get_db)
):
    """Обновить количество товара в корзине"""
    print(f"=== UPDATE: product_id={product_id}, quantity={quantity} ===")
    
    current_user = await auth.get_current_user_optional(request, db=db)
    
    if current_user:
        # Авторизованный - обновляем в БД    
        stmt = select(models.CartItem).filter(
            models.CartItem.user_id == current_user.id,
            models.CartItem.product_id == product_id)
        result = await db.execute(stmt)
        cart_item = result.scalars().first()
        if cart_item:
            if quantity <= 0:
                db.delete(cart_item)
                print(f"Deleted item {product_id} from user cart")
            else:
                cart_item.quantity = quantity
                print(f"Updated item {product_id} to quantity {quantity}")
            db.commit()
        redirect_response = RedirectResponse(url="/cart", status_code=303)
        return redirect_response
    else:
        # Гость - обновляем cookie
        product_ids = get_cart_from_cookie(request)
        print(f"Current product_ids: {product_ids}")
        
        # Удаляем все вхождения товара
        product_ids = [pid for pid in product_ids if pid != product_id]
        
        # Добавляем новое количество
        for _ in range(quantity):
            product_ids.append(product_id)
        
        print(f"New product_ids: {product_ids}")
        # СОЗДАЕМ НОВЫЙ редирект и устанавливаем cookie
        redirect_response = RedirectResponse(url="/cart", status_code=303)
        
        if product_ids:
            cart_value = ",".join(map(str, product_ids))
            redirect_response.set_cookie(
                key="cart",
                value=cart_value,
                max_age=30*24*60*60,
                path="/"
            )
            print(f"Cookie updated: {cart_value[:50]}...")
        else:
            redirect_response.delete_cookie("cart", path="/")
            print("Cookie deleted (cart empty)")
        
        return redirect_response

@router.post("/remove/{product_id}")
async def remove_from_cart(
    product_id: int,
    request: Request = None,
    response: Response = None,
    db: AsyncSession = Depends(get_db)
):
    """Удалить товар из корзины полностью"""
    print(f"=== REMOVE: product_id={product_id} ===")
    
    current_user = await auth.get_current_user_optional(request, db=db)
    
    if current_user:
        # Авторизованный - удаляем из БД
        stmt = select(models.CartItem).filter(
            models.CartItem.user_id == current_user.id,
            models.CartItem.product_id == product_id)
        result = await db.execute(stmt)
        cart_item = result.scalars().first()
        if cart_item:
            await db.delete(cart_item)
            await db.commit()
            print(f"Removed item {product_id} from user cart")
        redirect_response = RedirectResponse(url="/cart", status_code=303)
        return redirect_response
    else:
        # Гость - удаляем из cookie
        product_ids = get_cart_from_cookie(request)
        print(f"Before: {product_ids}")
        
        # Удаляем все вхождения товара
        original_len = len(product_ids)
        product_ids = [pid for pid in product_ids if pid != product_id]
        print(f"After: {product_ids}, removed {original_len - len(product_ids)} items")
        
        redirect_response = RedirectResponse(url="/cart", status_code=303)       
        if product_ids:
            cart_value = ",".join(map(str, product_ids))
            redirect_response.set_cookie(
                key="cart",
                value=cart_value,
                max_age=30*24*60*60,
                path="/"
            )
            print(f"Cookie updated: {cart_value[:50]}...")
        else:
            redirect_response.delete_cookie("cart", path="/")
            print("Cookie deleted (cart empty)")
        
        return redirect_response

@router.post("/clear")
async def clear_cart(
    request: Request = None,
    response: Response = None,
    db: AsyncSession = Depends(get_db)
):
    """Очистить корзину полностью"""
    print(f"=== CLEAR CART ===")
    current_user = await auth.get_current_user_optional(request, db=db)
    
    if current_user:
        # Удаляем элементы корзины пользователя
        stmt = delete(models.CartItem).filter(models.CartItem.user_id == current_user.id)
        result = await db.execute(stmt)
        await db.commit()
        deleted = result.rowcount
        print(f"Cleared {deleted} items from user cart")
    else:
        print("Clearing guest cart")
        print(f"Cookies before: {request.cookies}")
        # ВАЖНО: СОЗДАЕМ RedirectResponse и СРАЗУ удаляем cookie
        redirect_response = RedirectResponse(url="/cart", status_code=303)
        redirect_response.delete_cookie("cart", path="/")
        print("Guest cart cookie cleared in redirect_response")
        print(f"Cookies after (will be deleted): cart")
        return redirect_response
    
    return RedirectResponse(url="/cart", status_code=303)
