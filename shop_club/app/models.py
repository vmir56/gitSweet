from .database import Base
from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, DateTime, Boolean, BigInteger, Identity
from sqlalchemy.orm import relationship, Mapped, mapped_column
from typing import List, Optional
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    password: Mapped[str] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Связи
    orders: Mapped[List["Order"]] = relationship(back_populates="user")
    cart_items: Mapped[List["CartItem"]] = relationship(back_populates="user")

    def __repr__(self):
        return f"User(id={self.id!r}, username={self.username!r}, email={self.email!r})"

class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    price: Mapped[float] = mapped_column(nullable=False)
    stock: Mapped[int] = mapped_column(Integer, default=0)  # Добавим остаток
    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # URL картинки
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # 👇 ПОЛЯ ДЛЯ АНАЛОГОВ
    user_id: Mapped[int] = mapped_column(nullable=True, default=0)  # для идентификации автора записи
    old_price: Mapped[Optional[float]] = mapped_column(nullable=True)
    is_analog: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    source: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # ozon, wildberries
    source_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    analog_query: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # по какому запросу нашли
    
    # Связи
    category: Mapped[Optional["Category"]] = relationship(back_populates="products")
    cart_items: Mapped[List["CartItem"]] = relationship(back_populates="product", passive_deletes=True)
    # Это запретит SQLAlchemy выставлять NULL и заставит базу применить ON DELETE CASCADE
    order_items: Mapped[List["OrderItem"]] = relationship(back_populates="product", passive_deletes=True)

    def __repr__(self):
        analog_marker = " [АНАЛОГ]" if self.is_analog else ""
        return f"Product(id={self.id!r}, name={self.name!r}, price={self.price!r}{analog_marker})"

class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Связи - исправлено (было categories, должно быть category)
    products: Mapped[List["Product"]] = relationship(back_populates="category")

    def __repr__(self):
        return f"Category(id={self.id!r}, name={self.name!r})"

class CartItem(Base):
    __tablename__ = "cart_items"
    
    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи
    user: Mapped[Optional["User"]] = relationship(back_populates="cart_items")
    product: Mapped["Product"] = relationship(back_populates="cart_items")

class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    total_price: Mapped[float] = mapped_column(default=0)
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending, paid, shipped, delivered, cancelled
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Связи
    user: Mapped["User"] = relationship(back_populates="orders")
    order_items: Mapped[List["OrderItem"]] = relationship(back_populates="order")

    def __repr__(self):
        return f"Order(id={self.id!r}, user_id={self.user_id!r}, total_price={self.total_price!r})"

class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    price_at_time: Mapped[float] = mapped_column(Float)  # Цена на момент покупки
    
    # Связи
    order: Mapped["Order"] = relationship(back_populates="order_items")
    product: Mapped["Product"] = relationship(back_populates="order_items")
    
    def __repr__(self):
        return f"OrderItem(id={self.id!r}, order_id={self.order_id!r}, product_id={self.product_id!r}, quantity={self.quantity!r})"
