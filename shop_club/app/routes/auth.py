#app.routes.auth.py
from fastapi.responses import HTMLResponse, RedirectResponse, Response, JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from collections import Counter

from ..database import get_db
from .. import models, auth

from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, Depends, Request, Response, APIRouter, Form
from fastapi.security import OAuth2PasswordRequestForm
from starlette.responses import RedirectResponse

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


async def sync_cookie_cart_to_db(db: AsyncSession, user_id: int, cart_cookie: str):
    """Перенести корзину из cookie в БД"""
    if not cart_cookie:
        print("No cart cookie to sync")
        return
    
    # Парсим cookie
    if cart_cookie.startswith('"') and cart_cookie.endswith('"'):
        cart_cookie = cart_cookie[1:-1]
    cart_cookie = cart_cookie.replace('\\054', ',')
    
    product_ids = []
    for part in cart_cookie.split(','):
        part = part.strip()
        if part and part.isdigit():
            product_ids.append(int(part))
    
    if not product_ids:
        return
    
    # Группируем одинаковые товары
    counts = Counter(product_ids)
    print(f"Syncing cart: {dict(counts)}")
    
    for product_id, quantity in counts.items():
        # Проверяем существование товара
        stmt = select(models.Product).filter(models.Product.id == product_id)
        result = await db.execute(stmt)
        product = result.scalars().first()
        if not product:
            print(f"Product {product_id} not found, skipping")
            continue
        
        # Проверяем есть ли уже такой товар у пользователя
        stmt = select(models.CartItem).filter(
            models.CartItem.user_id == user_id,
            models.CartItem.product_id == product_id)
        result = await db.execute(stmt)
        existing = result.scalars().first()
        
        if existing:
            existing.quantity += quantity
            print(f"Updated existing: {product.name} +{quantity} = {existing.quantity}")
        else:
            new_item = models.CartItem(
                user_id=user_id,
                product_id=product_id,
                quantity=quantity
            )
            db.add(new_item)
            print(f"Added new: {product.name} x{quantity}")
    
    await db.commit()
    print(f"Cart sync completed for user {user_id}")


# ========== СТРАНИЦЫ ==========

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Страница входа"""
    return templates.TemplateResponse(
        request=request, 
        name="login.html"
    )
####### ОБЪЕДИНЕННЫЙ POST логин {"detail":"Method Not Allowed"} это post? надо get выше
@router.post("/login")
async def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    request: Request = None,
    response: Response = None,
    db: AsyncSession = Depends(get_db)  # Убедитесь, что вы используете AsyncSession # error no attribute 'query'
):
    # Аутентификация (no attribute 'query')
    stmt = select(models.User).where(models.User.username == form_data.username)
    result = await db.execute(stmt)
    db_user = result.scalars().first()
    
    if db_user is None or not auth.verify_password(form_data.password, db_user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Переносим корзину из cookie в БД
    cart_cookie = request.cookies.get("cart", "")
    if cart_cookie:
        print(f"Form login: syncing cart cookie: {cart_cookie[:50]}...")
        await sync_cookie_cart_to_db(db, db_user.id, cart_cookie)
    
    # Генерация токена
    access_token = auth.create_access_token(data={"sub": str(db_user.id)})
    
    # Определяем тип клиента по заголовку Accept, вариант для JSON и мобильных
    accept_header = request.headers.get("accept", "")
    
    # Если клиент ожидает JSON (Swagger, API, мобильное приложение)
    if "application/json" in accept_header or "/api" in str(request.url):
        return {"access_token": access_token, "token_type": "bearer"}
    
    # Иначе - HTML форма (браузер)
    redirect_response = RedirectResponse(url="/", status_code=303)
    redirect_response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=30 * 24 * 60 * 60,
        path="/"
    )
    return redirect_response

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Страница регистрации"""
    return templates.TemplateResponse(
        request=request, 
        name="register.html"
    )

@router.get("/logout")
async def logout(response: Response):
    """Выход из системы"""
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("access_token", path="/")
    return response


# ========== API ДЛЯ SWAGGER (JSON) ==========

@router.post("/api/login", response_model=dict)
async def login_api(
    form_data: OAuth2PasswordRequestForm = Depends(),
    request: Request = None,
    db: AsyncSession = Depends(get_db)
):
    """API логин для Swagger UI"""
    # Аутентификация
    stmt = select(models.User).filter(models.User.username == form_data.username)
    result = await db.execute(stmt)
    db_user = result.scalars().first()
    
    if db_user is None or not auth.verify_password(form_data.password, db_user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Переносим корзину из cookie в БД
    cart_cookie = request.cookies.get("cart", "")
    if cart_cookie:
        print(f"API login: syncing cart cookie: {cart_cookie[:50]}...")
        await sync_cookie_cart_to_db(db, db_user.id, cart_cookie)
    
    # Генерация токена
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(data={"sub": str(db_user.id)}, expires_delta=access_token_expires)
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/register", response_model=dict)
async def register_form(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """Регистрация нового пользователя"""
    # Проверка существующего пользователя
    stmt_username = select(models.User).filter(models.User.username == username)
    result_username = await db.execute(stmt_username)
    db_user = result_username.scalars().first()
    
    if db_user:
        return templates.TemplateResponse(
            request=request,
            name="register.html",
            context={"error": "Username already registered"}
        )
    
    stmt_email = select(models.User).filter(models.User.email == email)
    result_email = await db.execute(stmt_email)
    db_email = result_email.scalars().first()
    
    if db_email:
        return templates.TemplateResponse(
            request=request,
            name="register.html",
            context={"error": "Email already registered"}
        )
    
    # Создание пользователя
    hashed_password = auth.get_password_hash(password)
    new_user = models.User(
        username=username,
        email=email,
        password=hashed_password
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    print(f"New user registered: {username} (id={new_user.id})")
    
    # Переносим корзину из cookie в БД
    cart_cookie = request.cookies.get("cart", "")
    if cart_cookie:
        print(f"Register: syncing cart cookie: {cart_cookie[:50]}...")
        await sync_cookie_cart_to_db(db, new_user.id, cart_cookie)
    
    # Генерация токена
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(data={"sub": str(new_user.id)}, expires_delta=access_token_expires)
    
    # Создаем ответ
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=30 * 24 * 60 * 60,
        path="/"
    )
    
    # Удаляем cookie корзины
    response.delete_cookie("cart", path="/")
    
    return response

#async def sync_cookie_cart_to_db(db: AsyncSession, user_id: int, cart_cookie: str):
    # Логика синхронизации корзины из cookie в БД
    # Пример реализации:
    # Разбираем cart_cookie и добавляем товары в корзину пользователя
    #pass