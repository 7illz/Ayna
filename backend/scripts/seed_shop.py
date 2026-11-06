"""Explicit development-only sample catalog; never run automatically in production."""

from pathlib import Path

from sqlalchemy import select

from app.common.config import get_settings
from app.common.db import SessionLocal
from app.common.identity import password_hash
from app.common.models import Product, ProductImage, new_id
from app.common.storage import get_storage
from app.modules.catalog.routes import sanitize_image
from app.modules.commerce.models import Category, Coupon, StoreSettings, User, Variant
from app.modules.commerce.service import DEFAULT_CATEGORIES

DEMO_PASSWORD = "AynaDemo!2026"
DEMO_SELLER = "11111111-1111-4111-8111-111111111111"
PRODUCTS = [
    (
        "headphones",
        "Wireless over-ear headphones",
        "electronics",
        649000,
        799000,
        18,
        "Make room for your favorite sound. A comfortable everyday listening companion.",
        True,
    ),
    (
        "bag",
        "Everyday shoulder bag",
        "bags",
        425000,
        None,
        12,
        "An easy carry for days on the move. Thoughtful details, a timeless silhouette.",
        True,
    ),
    (
        "shoes",
        "Everyday red sneakers",
        "shoes",
        549000,
        690000,
        20,
        "A bold little step for your everyday rotation. Select your preferred size.",
        True,
    ),
    (
        "shirt",
        "Essential cotton tee",
        "shirts",
        149000,
        189000,
        30,
        "A clean, versatile layer for an effortless everyday wardrobe. Soft cotton feel.",
        True,
    ),
    (
        "dress",
        "Weekend summer dress",
        "shirts",
        349000,
        None,
        16,
        "An airy silhouette for slow weekends and brighter days. Available in multiple sizes.",
        False,
    ),
    (
        "lamp",
        "Warm glow table lamp",
        "home",
        289000,
        359000,
        9,
        "A softer corner of your home. A simple lighting accent for desks and bedside tables.",
        True,
    ),
    (
        "watch",
        "Minimal everyday watch",
        "accessories",
        399000,
        None,
        14,
        "A considered finishing touch. A classic watch silhouette for everyday wear.",
        False,
    ),
    (
        "camera",
        "Compact mirrorless camera",
        "electronics",
        7490000,
        None,
        5,
        "See the familiar from a new perspective. An illustrative camera listing for this demo.",
        False,
    ),
]


def main():
    if get_settings().environment == "production":
        raise SystemExit("Demo seeding is forbidden in production")
    root = Path(__file__).resolve().parents[1] / "fixtures" / "demo"
    with SessionLocal() as db:
        for email, name, role in [
            ("admin@ayna.local", "Ayna Administrator", "admin"),
            ("seller@ayna.local", "Ayna Studio", "seller"),
            ("shopper@ayna.local", "Demo Shopper", "customer"),
        ]:
            user = db.scalar(select(User).where(User.email == email))
            if user is None:
                user = User(
                    email=email, name=name, role=role, password_hash=password_hash(DEMO_PASSWORD)
                )
                if role == "seller":
                    if db.get(User, DEMO_SELLER) is not None:
                        raise SystemExit("The reserved demo seller ID is already in use")
                    user.id = DEMO_SELLER
                db.add(user)
        for slug, name in DEFAULT_CATEGORIES.items():
            if db.get(Category, slug) is None:
                db.add(Category(slug=slug, name=name))
        if db.get(StoreSettings, 1) is None:
            db.add(StoreSettings(id=1))
        if db.get(Coupon, "WELCOME10") is None:
            db.add(
                Coupon(code="WELCOME10", discount_percent=10, minimum_minor=100000, max_uses=1000)
            )
        db.commit()
        for key, name, category, price, compare, stock, description, featured in PRODUCTS:
            sku = f"AY-DEMO-{key.upper()}"
            if db.scalar(select(Product.id).where(Product.sku == sku)):
                continue
            product = Product(
                id=new_id(),
                seller_id=DEMO_SELLER,
                name=name,
                category=category,
                description=description
                + " Demo listing: illustrative photography; no item is for sale.",
                price_minor=price,
                compare_at_minor=compare,
                stock=stock,
                brand="Studio selection",
                sku=sku,
                is_listed=True,
                featured=featured,
            )
            db.add(product)
            db.flush()
            raw = (root / f"{key}.jpg").read_bytes()
            clean = sanitize_image(raw, "image/jpeg")
            image_id = new_id()
            prefix = f"products/{product.id}/{image_id}"
            get_storage().put(f"{prefix}/original", raw, "image/jpeg")
            get_storage().put(f"{prefix}/photo.png", clean, "image/png")
            product.images.append(
                ProductImage(
                    id=image_id,
                    storage_key=f"{prefix}/photo.png",
                    original_key=f"{prefix}/original",
                    view_tag="front",
                    sort_order=0,
                )
            )
            if category in {"shirts", "shoes"}:
                sizes = (
                    ["38", "39", "40", "41", "42"] if category == "shoes" else ["S", "M", "L", "XL"]
                )
                for size in sizes:
                    db.add(
                        Variant(
                            product_id=product.id,
                            label=size,
                            size=size,
                            sku=f"{sku}-{size}",
                            price_minor=price,
                            stock=max(2, stock // len(sizes)),
                        )
                    )
            db.commit()
    print("Ayna sample catalog ready. Development accounts: shopper/seller/admin@ayna.local")
    print("Local-only password: AynaDemo!2026")


if __name__ == "__main__":
    main()
