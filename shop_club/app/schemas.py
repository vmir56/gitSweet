from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# Схема для аналогов товара

class AnalogCreate(BaseModel):
    name: str
    price: float
    old_price: Optional[float] = None
    image_url: Optional[str] = None
    source: str = "ozon"
    source_url: Optional[str] = None
    analog_query: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[int] = None

# Схема для товара
class ProductCreate(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    category_id: int
    stock: int = 0
    image_url: Optional[str] = None

# Схема для ОБНОВЛЕНИЯ товара (все поля НЕобязательны)
class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    category_id: Optional[int] = None
    stock: Optional[int] = None
    image_url: Optional[str] = None

class ProductResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    price: float
    stock: int
    image_url: Optional[str] = None
    category_id: Optional[int] = None
    old_price: Optional[float] = None
    is_analog: bool = False
    source: Optional[str] = None
    source_url: Optional[str] = None
    analog_query: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Схема для категории
class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None

class CategoryResponse(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True

# Схема для пользователя
class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str

    class Config:
        from_attributes = True

# Схема для заказа
class OrderCreate(BaseModel):
    user_id: int
    product_ids: List[int]

class OrderResponse(BaseModel):
    id: int
    user_id: int
    product_ids: List[int]
    total_price: float

    class Config:
        from_attributes = True