# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .routes import admin, auth, frontend, orders, products, cart
#from .database import engine, Base
from app.database import engine, Base  # engine должен быть AsyncEngine
from .models import User, Product
from app.api.v1.endpoints import spider, analog
from app.routes import search


# 👇 СОЗДАЁМ LIFESPAN ДЛЯ АСИНХРОННОГО СОЗДАНИЯ ТАБЛИЦ
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Выполняется при старте
    print("🚀 Creating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database tables created/verified")
    
    yield  # Приложение работает
    
    # Выполняется при остановке
    print("🛑 Shutting down...")
    await engine.dispose()


# Создаём приложение с lifespan
app = FastAPI(
    title="Shop Club",
    lifespan=lifespan  # 👈 ПОДКЛЮЧАЕМ LIFESPAN
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

# CORS настройки
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(products.router, prefix="/products", tags=["products"])
app.include_router(orders.router, prefix="/orders", tags=["orders"])
app.include_router(cart.router, prefix="/cart", tags=["cart"])
app.include_router(frontend.router, tags=["frontend"])
app.include_router(spider.router, prefix="/api/v1", tags=["spider"])
app.include_router(analog.router, prefix="/api/v1", tags=["analog"]) 
app.include_router(search.router)


@app.get("/")
async def root():
    return {"message": "Shop Club API"}

'''
Если использовать Alembic для управления схемой БД (правильно для продакшена), 
то строку с create_all убрать, оставив только:
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Проверяем, что БД доступна (опционально)
    async with engine.begin() as conn:
        await conn.execute("SELECT 1")
    yield
    await engine.dispose()
миграции отдельно:
./venv/bin/python -m alembic upgrade head
'''