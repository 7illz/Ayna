from datetime import datetime

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.common.db import Base
from app.common.models import new_id, now


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="customer")
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AuthThrottle(Base):
    __tablename__ = "auth_throttles"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    count: Mapped[int] = mapped_column(default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ResetToken(Base):
    __tablename__ = "password_resets"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used: Mapped[bool] = mapped_column(default=False)


class Address(Base):
    __tablename__ = "addresses"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    label: Mapped[str] = mapped_column(String(50), default="Home")
    recipient: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(30))
    street: Mapped[str] = mapped_column(String(300))
    city: Mapped[str] = mapped_column(String(100))
    postal_code: Mapped[str] = mapped_column(String(20))
    country: Mapped[str] = mapped_column(String(2), default="BD")


class Category(Base):
    __tablename__ = "categories"
    slug: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(String(300), default="")
    is_active: Mapped[bool] = mapped_column(default=True)


class Variant(Base):
    __tablename__ = "product_variants"
    __table_args__ = (
        CheckConstraint("stock >= 0", name="variant_stock_nonnegative"),
        CheckConstraint("price_minor >= 0", name="variant_price_nonnegative"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), index=True)
    label: Mapped[str] = mapped_column(String(100))
    sku: Mapped[str] = mapped_column(String(80), unique=True)
    size: Mapped[str] = mapped_column(String(30), default="")
    color: Mapped[str] = mapped_column(String(40), default="")
    stock: Mapped[int] = mapped_column(default=0)
    price_minor: Mapped[int] = mapped_column(default=0)
    is_active: Mapped[bool] = mapped_column(default=True)


class CartItem(Base):
    __tablename__ = "cart_items"
    __table_args__ = (UniqueConstraint("user_id", "product_id", "variant_key"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"))
    variant_key: Mapped[str] = mapped_column(String(36), default="default")
    quantity: Mapped[int] = mapped_column(default=1)


class Wishlist(Base):
    __tablename__ = "wishlist"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), primary_key=True)


class Coupon(Base):
    __tablename__ = "coupons"
    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    discount_percent: Mapped[int] = mapped_column(default=0)
    discount_minor: Mapped[int] = mapped_column(default=0)
    minimum_minor: Mapped[int] = mapped_column(default=0)
    max_uses: Mapped[int] = mapped_column(default=100)
    used_count: Mapped[int] = mapped_column(default=0)
    is_active: Mapped[bool] = mapped_column(default=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (UniqueConstraint("user_id", "idempotency_key"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    number: Mapped[str] = mapped_column(String(40), unique=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(30), default="placed")
    payment_method: Mapped[str] = mapped_column(String(20))
    payment_status: Mapped[str] = mapped_column(String(30), default="pending")
    stripe_session_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    stripe_payment_id: Mapped[str | None] = mapped_column(String(255))
    currency: Mapped[str] = mapped_column(String(3), default="BDT")
    subtotal_minor: Mapped[int]
    discount_minor: Mapped[int] = mapped_column(default=0)
    shipping_minor: Mapped[int] = mapped_column(default=0)
    tax_minor: Mapped[int] = mapped_column(default=0)
    total_minor: Mapped[int]
    coupon_code: Mapped[str | None] = mapped_column(String(32))
    shipping_address: Mapped[dict] = mapped_column(JSON)
    notes: Mapped[str] = mapped_column(String(1000), default="")
    return_reason: Mapped[str] = mapped_column(String(1000), default="")
    stock_released: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class OrderItem(Base):
    __tablename__ = "order_items"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"))
    variant_key: Mapped[str] = mapped_column(String(36), default="default")
    seller_id: Mapped[str] = mapped_column(String(36), index=True)
    name: Mapped[str] = mapped_column(String(160))
    variant_label: Mapped[str] = mapped_column(String(100), default="")
    sku: Mapped[str] = mapped_column(String(80), default="")
    unit_price_minor: Mapped[int]
    quantity: Mapped[int]
    fulfillment_status: Mapped[str] = mapped_column(String(20), default="pending")
    tracking_number: Mapped[str] = mapped_column(String(100), default="")
    courier: Mapped[str] = mapped_column(String(80), default="")


class OrderEvent(Base):
    __tablename__ = "order_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), index=True)
    status: Mapped[str] = mapped_column(String(30))
    message: Mapped[str] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (UniqueConstraint("user_id", "product_id"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    rating: Mapped[int]
    title: Mapped[str] = mapped_column(String(160))
    body: Mapped[str] = mapped_column(String(2000))
    is_visible: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(120))
    message: Mapped[str] = mapped_column(String(1000))
    is_read: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SupportTicket(Base):
    __tablename__ = "support_tickets"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    subject: Mapped[str] = mapped_column(String(160))
    message: Mapped[str] = mapped_column(String(3000))
    status: Mapped[str] = mapped_column(String(20), default="open")
    response: Mapped[str] = mapped_column(String(3000), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class StoreSettings(Base):
    __tablename__ = "store_settings"
    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    name: Mapped[str] = mapped_column(String(80), default="Ayna")
    tagline: Mapped[str] = mapped_column(String(160), default="Everyday finds. A new perspective.")
    shipping_minor: Mapped[int] = mapped_column(default=8000)
    free_shipping_minor: Mapped[int] = mapped_column(default=300000)
    tax_basis_points: Mapped[int] = mapped_column(default=0)
    support_email: Mapped[str] = mapped_column(String(254), default="support@example.com")
    announcement: Mapped[str] = mapped_column(
        String(200), default="Free delivery on orders over ৳3,000"
    )
