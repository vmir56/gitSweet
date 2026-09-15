# product_service.py
from ..models import Product
from ..schemas import ProductCreate
from sqlalchemy.orm import Session


# Асинхронное добавление товара в базу данных
async def create_product(product: ProductCreate, db: Session):
    db_product = Product(**product.dict())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product