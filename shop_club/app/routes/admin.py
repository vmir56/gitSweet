from typing import List, Optional
from fastapi import UploadFile, File, Form, Cookie, APIRouter, HTTPException, Request, status, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from .. import models, schemas, auth, database
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from urllib.parse import urlparse
import shutil, re, os
from pathlib import Path
# from database import get_db

from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal

from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from jinja2 import Template

router = APIRouter()
#router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="app/templates")
UPLOAD_DIR = Path("static/images")

# Получаем сессию базы данных
# ✅ НОВЫЙ АСИНХРОННЫЙ КОД
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# Создаем папку для изображений
UPLOAD_DIR = Path("app/static/images")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/upload-image")
async def upload_image(
    request: Request,
    file: UploadFile = File(...),
    product_id: Optional[int] = Form(None), 
    # УБРАЛ Depends(auth.get_current_user), чтобы FastAPI не выкидывал 401 на входе
    db: Session = Depends(get_db)
):
    # print("LoadImg\n")  

    # Получаем пользователя (функция должна уметь читать и куки, и заголовки)
    current_user = await auth.get_current_user_optional(request, db=db)
    print(f"(LoadImg)Current user: {current_user.username if current_user else 'None'}")

    # Защита эндпоинта: если пользователя нет или он не админ — даем от ворот поворот
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if current_user.username != "admin":  # Раскомментируйте, когда убедитесь, что юзер находится
        raise HTTPException(status_code=403, detail="Admin only")

    # Проверяем тип файла
    allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid image type")
    
    # Генерируем уникальное имя файла
    import uuid
    import shutil
    ext = file.filename.split('.')[-1]
    filename = f"{uuid.uuid4().hex}.{ext}"
    file_path = UPLOAD_DIR / filename
    
    # Сохраняем файл
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Возвращаем URL для доступа к изображению
    image_url = f"/static/images/{filename}"
    return {"image_url": image_url}

def validate_image_url(url: str) -> bool:
    """Проверка валидности URL изображения"""
    if not url:
        return True  # Пустой URL допустим
    
    # Проверяем формат URL
    try:
        result = urlparse(url)
        if not all([result.scheme, result.netloc]):
            return False
        if result.scheme not in ['http', 'https']:
            return False
        # Проверяем расширение файла
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']
        path = result.path.lower()
        if not any(path.endswith(ext) for ext in allowed_extensions):
            return False
        return True
    except:
        return False

# Только администратор
def admin_required(current_user: models.User = Depends(auth.get_current_user)):
    if current_user.username != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    return current_user

# CRUD страница управления товарами (GET)
@router.get("/crud_products", response_class=HTMLResponse)
async def crud_products(
    request: Request,
    db: AsyncSession = Depends(get_db),
    # current_user: models.User = Depends(admin_required)
):
    current_user = await auth.get_current_user_optional(request, db=db)
    
    # Получение продуктов
    stmt_products = select(models.Product)
    result_products = await db.execute(stmt_products)
    products = result_products.scalars().all()
    
    # Получение категорий
    stmt_categories = select(models.Category)
    result_categories = await db.execute(stmt_categories)
    categories = result_categories.scalars().all()
    
    categories_dict = {c.id: c.name for c in categories}
    
    return templates.TemplateResponse(
        request=request,
        name="admin_products.html",
        context={
            "products": products,
            "categories": categories_dict,
            "current_user": current_user
        }
    )

# Добавление товара
@router.get("/products", response_class=HTMLResponse)
async def login_page(request: Request):
    """Страница входа"""
    return templates.TemplateResponse(
        request=request, 
        name="product.html"
    )
@router.post("/products", response_model=schemas.ProductResponse)
async def add_product(
    request: Request,
    product: schemas.ProductCreate,
    db: Session = Depends(get_db)
    #current_user: models.User = Depends(auth.get_current_user)
):
    current_user = await auth.get_current_user_optional(request, db=db)
    print(f"(Prod)Current user: {current_user.username if current_user else 'None'}")
    # Валидация URL
    #if product.image_url and not validate_image_url(product.image_url):
    #    raise HTTPException(status_code=400, detail="Invalid image URL format")
    db_product = models.Product(**product.dict())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

# Обновление товара
@router.put("/products/{product_id}", response_model=schemas.ProductResponse)
async def update_product(
    product_id: int,
    product: schemas.ProductCreate,
    db: AsyncSession = Depends(get_db)
): #, current_user: models.User = Depends(admin_required)):
    stmt = select(models.Product).filter(models.Product.id == product_id)
    result = await db.execute(stmt)
    db_product = result.scalars().first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    db_product.name = product.name
    db_product.description = product.description
    db_product.price = product.price
    db_product.category_id = product.category_id
    db_product.stock = product.stock
    db_product.image_url = product.image_url 

    await db.commit()
    await db.refresh(db_product)
    return db_product

# Удаление товара
@router.get("/products/{product_id}", response_class=HTMLResponse)
async def login_page_delete(request: Request):
    return templates.TemplateResponse(
        request=request, 
        name="admin_products.html"
    )

# --- ИСПРАВЛЕННЫЙ UPDATE PRODUCT ---
@router.put("/products/{product_id}", response_model=schemas.ProductResponse)
async def update_product(
    product_id: int,
    request: Request,
    product_data: schemas.ProductUpdate,
    db: AsyncSession = Depends(get_db)
):
    current_user = await auth.get_current_user_optional(request, db=db)
    if not current_user or current_user.username != "admin":
        raise HTTPException(status_code=401, detail="Unauthorized")

    stmt = select(models.Product).filter(models.Product.id == product_id)
    result = await db.execute(stmt)
    db_product = result.scalars().first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    # НАДЕЖНАЯ ПРОВЕРКА: удаляем старый файл только если НОВЫЙ URL пришел,
    # он отличается от старого, и СТАРЫЙ URL действительно существует (не None и не пустой)
    if product_data.image_url and product_data.image_url != db_product.image_url:
        if db_product.image_url: # Проверка, что старый url не None
            old_filename = db_product.image_url.split("/")[-1]
            old_file_path = UPLOAD_DIR / old_filename
        # БЕЗОПАСНОСТЬ: os.remove сработает ТОЛЬКО если файл реально лежит на диске
        if old_file_path.exists() and old_file_path.is_file():
            try:
                os.remove(old_file_path)
                print(f"Успешно удалён старый файл: {old_filename}")
            except Exception as e:
                print(f"Не удалось удалить файл с диска: {e}")
        else:
            print(f"Старого файла {old_filename} не было на диске. Пропускаем удаление.")

    # Обновляем поля
    update_data = product_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_product, key, value)

    await db.commit()
    await db.refresh(db_product)
    return db_product

# --- ИСПРАВЛЕННЫЙ DELETE PRODUCT ---
@router.delete("/products/{product_id}")
async def delete_product(
    product_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    current_user = await auth.get_current_user_optional(request, db=db)
    if not current_user or current_user.username != "admin":
        raise HTTPException(status_code=401, detail="Unauthorized")

    stmt = select(models.Product).filter(models.Product.id == product_id)
    result = await db.execute(stmt)
    db_product = result.scalars().first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    # НАДЕЖНАЯ ПРОВЕРКА: удаляем файл с диска только если строка image_url существует
    if db_product.image_url: # Если тут None, этот блок просто пропустится
        filename = db_product.image_url.split("/")[-1]
        file_path = UPLOAD_DIR / filename
        if file_path.exists():
            os.remove(file_path)

    await db.delete(db_product)
    await db.commit()
    return {"status": "success", "message": f"Product {product_id} deleted successfully"}

# Просмотр всех заказов
@router.get("/orders", response_model=List[schemas.OrderResponse])
async def get_orders(db: AsyncSession = Depends(get_db), current_user: models.User = Depends(admin_required)): 
    stmt = select(models.Order)
    result = await db.execute(stmt)
    db_orders = result.scalars().all()    
    return db_orders

# Обновление статуса заказа
@router.put("/orders/{order_id}", response_model=schemas.OrderResponse)
async def update_order_status(order_id: int, status: str, db: AsyncSession = Depends(get_db), current_user: models.User = Depends(admin_required)):
    stmt = select(models.Order).filter(models.Order.id == order_id)
    result = await db.execute(stmt)
    db_order = result.scalars().first()    
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    db_order.status = status
    await db.commit()
    await db.refresh(db_order)
    return db_order

# Просмотр всех пользователей
@router.get("/users", response_model=List[schemas.UserResponse])
async def get_users(db: AsyncSession = Depends(get_db), current_user: models.User = Depends(admin_required)):

    stmt = select(models.User)
    result = await db.execute(stmt)
    db_users = result.scalars().all()    
    return db_users

# Блокировка пользователя
@router.put("/users/{user_id}/block", response_model=schemas.UserResponse)
async def block_user(user_id: int, db: AsyncSession = Depends(get_db), current_user: models.User = Depends(admin_required)):

    stmt = select(models.User).filter(models.User.id == user_id)
    result = await db.execute(stmt)
    db_user = result.scalars().first()    
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db_user.is_active = False  # Блокируем пользователя
    await db.commit()
    await db.refresh(db_user)
    return db_user

# Удаление пользователя
@router.delete("/users/{user_id}", response_model=schemas.UserResponse)
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db), current_user: models.User = Depends(admin_required)):

    stmt = select(models.User).filter(models.User.id == user_id)
    result = await db.execute(stmt)
    db_user = result.scalars().first()    
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    await db.delete(db_user)
    await db.commit()
    return db_user


# API для получения категорий (с авторизацией)
@router.get("/categories")
async def get_categories_api(
    db: AsyncSession = Depends(get_db),
    #current_user: models.User = Depends(admin_required)
):
    # Получение категорий
    stmt_categories = select(models.Category)
    result_categories = await db.execute(stmt_categories)
    categories = result_categories.scalars().all()
    return [{"id": c.id, "name": c.name, "description": c.description} for c in categories]

@router.post("/categories", response_model=schemas.CategoryResponse)
async def add_category(
    category: schemas.CategoryCreate,
    db: AsyncSession = Depends(get_db)
    ): #, current_user: models.User = Depends(admin_required))  # ← ЭТОТ ПАРАМЕТР НУЖЕН
    # db_category = models.Category(**categories.dict())
    db_category = models.Category(
        name=category.name,
        description=category.description
    )
    db.add(db_category)
    await db.commit()
    await db.refresh(db_category)
    return db_category

### To complete the crud

# --- UPDATE PRODUCT ---
@router.put("/products/{product_id}", response_model=schemas.ProductResponse)
async def update_product(
    product_id: int,
    request: Request,
    product_data: schemas.ProductUpdate, # Используем новую схему обновлений
    db: AsyncSession = Depends(get_db)
):
    # Проверка авторизации
    current_user = await auth.get_current_user_optional(request, db=db)
    if not current_user or current_user.username != "admin":
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Ищем товар в БД
    stmt = select(models.Product).filter(models.Product.id == product_id)
    result = await db.execute(stmt)
    db_product = result.scalars().first()    
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Умное удаление старой картинки при замене на новую
    if product_data.image_url and product_data.image_url != db_product.image_url:
        if db_product.image_url:
            old_filename = db_product.image_url.split("/")[-1]
            old_file_path = UPLOAD_DIR / old_filename
            if old_file_path.exists():
                os.remove(old_file_path)

    # Обновляем в БД только те поля, которые прислал фронтенд
    update_data = product_data.model_dump(exclude_unset=True) # В Pydantic v2 используется model_dump() вместо dict()
    for key, value in update_data.items():
        setattr(db_product, key, value)

    await db.commit()
    await db.refresh(db_product)
    return db_product


# --- DELETE PRODUCT ---
@router.delete("/products/{product_id}")
async def delete_product(
    product_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    # Проверка авторизации
    current_user = await auth.get_current_user_optional(request, db=db)
    if not current_user or current_user.username != "admin":
        raise HTTPException(status_code=401, detail="Unauthorized")

    stmt = select(models.Product).filter(models.Product.id == product_id)
    result = await db.execute(stmt)
    db_product = result.scalars().first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Физически удаляем файл картинки с диска перед удалением из БД
    if db_product.image_url:
        filename = db_product.image_url.split("/")[-1]
        file_path = UPLOAD_DIR / filename
        if file_path.exists():
            os.remove(file_path)

    await db.delete(db_product)
    await db.commit()
    return {"status": "success", "message": f"Product {product_id} and its image deleted successfully"}

