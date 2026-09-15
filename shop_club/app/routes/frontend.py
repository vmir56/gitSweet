# app/routes/frontend.py
from fastapi.responses import HTMLResponse
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..database import get_db
from .. import auth, models

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
async def homepage(request: Request, db: AsyncSession = Depends(get_db)):
    # Передаем request и db (token не нужен, будет взят из cookie/header)
    current_user = await auth.get_current_user_optional(request, db)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"request": request, "current_user": current_user}
    )

# ========== КАТАЛОГ ТОВАРОВ ==========
@router.get("/catalog")
async def catalog(request: Request, db: AsyncSession = Depends(get_db)):
    # Асинхронный запрос через select
    result = await db.execute(select(models.Product))
    products = result.scalars().all()
    return templates.TemplateResponse(
        request=request,
        name="catalog.html",
        context={"request": request, "products": products}
    )

# ========== КАРТОЧКА ТОВАРА ==========
@router.get("/product/{product_id}")
async def product_detail(
    product_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(models.Product).where(models.Product.id == product_id)
    )
    product = result.scalar_one_or_none()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return templates.TemplateResponse(
        "product_detail.html",
        {"request": request, "product": product}
    )

@router.get("/debug-cookie")
async def debug_cookie(request: Request):
    """Проверка cookie"""
    raw_cookie = request.cookies.get("cart", "")
    parsed = get_cart_from_cookie(request)
    return {
        "raw_cookie": raw_cookie,
        "parsed_ids": parsed,
        "all_cookies": dict(request.cookies)
    }
