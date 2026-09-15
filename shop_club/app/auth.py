# shop_club/app/auth.py
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.core.config import settings  # 👈 ПОДКЛЮЧАЕМ НАСТРОЙКИ
from app import models
from app.database import get_db

from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

# 👇 ТЕПЕРЬ НАСТРОЙКИ БЕРУТСЯ ИЗ core/config.py
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def decode_token(token: str, db: AsyncSession):
    """Декодирует токен и возвращает пользователя"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
        
        # Создаем SQL-запрос с использованием select
        stmt = select(models.User).where(models.User.id == user_id) 
        # Выполняем запрос в асинхронной сессии
        result = await db.execute(stmt)
        # Получаем первого результата
        db_user = result.scalars().first()
        
        return db_user
    except JWTError:
        return None

async def get_current_user_optional(
    request: Request,
    db: AsyncSession = Depends(get_db),
    token: Optional[str] = None
):
    """Опциональная авторизация - возвращает пользователя или None"""
    # Если токен не передан, пробуем взять из header
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    
    # Пробуем из cookie
    if not token:
        token = request.cookies.get("access_token")
    
    if token:
        user = await decode_token(token, db)
        if user:
            return user
    
    return None

"""
async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    #token: str = Depends(oauth2_scheme)
):
    #######################################
    print(f"🔍 Токен из заголовка: {token}")
    print(f"🔍 Кука access_token: {request.cookies.get('access_token')}")
    ""Обязательная авторизация - возвращает пользователя или 401""
    user = await get_current_user_optional(request, db, token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user """

async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Получает пользователя из токена (сначала из куки, потом из заголовка)"""
    
    # 1. Пробуем взять токен из куки
    token = request.cookies.get("access_token")
    
    # 2. Если в куке нет — пробуем из заголовка Authorization
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
    
    # 3. Если токена нет — 401
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 4. Декодируем токен и получаем пользователя
    user = await decode_token(token, db)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user