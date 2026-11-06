from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import case, func, select
from sqlalchemy.exc import IntegrityError

from app.common.db import get_db
from app.common.identity import current_user, seller_user
from app.common.models import Product, ProductImage
from app.modules.catalog.routes import upload_images
from app.modules.commerce.models import Category, Order, OrderItem, Review, User, Variant, Wishlist
from app.modules.commerce.schemas import (
    ListingIn,
    MessageOut,
    ProductPage,
    ReviewIn,
    ReviewOut,
    ShopProduct,
    StoreConfig,
    VariantIn,
    VariantOut,
)
from app.modules.commerce.service import (
    DEFAULT_CATEGORIES,
    listed,
    page_count,
    product_view,
    store_config,
)
from app.modules.generation.tasks import latest_job
from app.modules.public_catalog.routes import stored_asset

router = APIRouter(tags=["Shopping and product management"])


@router.get("/shop/config", response_model=StoreConfig)
def config(db=Depends(get_db)):
    return store_config(db)


@router.get("/shop/products", response_model=ProductPage)
def products(
    q: str = Query(default="", max_length=120),
    category: str = "",
    brand: str = "",
    min_price: int = Query(default=0, ge=0),
    max_price: int | None = Query(default=None, ge=0),
    in_stock: bool = False,
    sort: str = Query(
        default="featured", pattern="^(featured|newest|price_asc|price_desc|name|rating)$"
    ),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=48),
    db=Depends(get_db),
):
    stmt = (
        select(Product)
        .outerjoin(User, User.id == Product.seller_id)
        .outerjoin(Category, Category.slug == Product.category)
        .where(
            Product.is_listed.is_(True),
            Product.is_archived.is_(False),
            (User.id.is_(None) | User.is_active.is_(True)),
            (Category.slug.is_(None) | Category.is_active.is_(True)),
            Product.price_minor >= min_price,
        )
    )
    if q.strip():
        escaped = q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        stmt = stmt.where(
            Product.name.ilike(pattern, escape="\\")
            | Product.description.ilike(pattern, escape="\\")
            | Product.brand.ilike(pattern, escape="\\")
        )
    if category:
        stmt = stmt.where(Product.category == category)
    if brand:
        stmt = stmt.where(Product.brand == brand)
    if max_price is not None:
        stmt = stmt.where(Product.price_minor <= max_price)
    if in_stock:
        variant_stock = (
            select(func.sum(Variant.stock))
            .where(Variant.product_id == Product.id, Variant.is_active.is_(True))
            .scalar_subquery()
        )
        any_variants = select(Variant.id).where(Variant.product_id == Product.id).exists()
        stmt = stmt.where(
            case((any_variants, func.coalesce(variant_stock, 0)), else_=Product.stock) > 0
        )
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    ordering = {
        "featured": (Product.featured.desc(), Product.created_at.desc()),
        "newest": (Product.created_at.desc(),),
        "price_asc": (Product.price_minor,),
        "price_desc": (Product.price_minor.desc(),),
        "name": (Product.name,),
    }
    if sort == "rating":
        rating = (
            select(func.avg(Review.rating))
            .where(Review.product_id == Product.id, Review.is_visible.is_(True))
            .scalar_subquery()
        )
        stmt = stmt.order_by(func.coalesce(rating, 0).desc(), Product.created_at.desc())
    else:
        stmt = stmt.order_by(*ordering[sort])
    rows = db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all()
    return ProductPage(
        items=[product_view(db, p) for p in rows],
        total=total,
        page=page,
        pages=page_count(total, page_size),
    )


@router.get("/shop/products/{product_id}", response_model=ShopProduct)
def detail(product_id: UUID, db=Depends(get_db)):
    return product_view(db, listed(db, str(product_id)))


@router.get("/shop/products/{product_id}/images/{image_id}")
def image(product_id: UUID, image_id: UUID, db=Depends(get_db)):
    listed(db, str(product_id))
    item = db.get(ProductImage, str(image_id))
    if item is None or item.product_id != str(product_id):
        raise HTTPException(404, "Image not found")
    return stored_asset(item.storage_key, "image/png")


@router.get("/shop/products/{product_id}/model")
def model(product_id: UUID, db=Depends(get_db)):
    product = listed(db, str(product_id))
    job = latest_job(db, product.id)
    if (
        product.publish_status != "approved"
        or not job
        or job.status != "succeeded"
        or not job.model_key
    ):
        raise HTTPException(404, "An approved 3D preview is not available")
    return stored_asset(job.model_key, "model/gltf-binary")


@router.get("/shop/products/{product_id}/reviews", response_model=list[ReviewOut])
def reviews(product_id: UUID, db=Depends(get_db)):
    listed(db, str(product_id))
    rows = db.execute(
        select(Review, User.name)
        .join(User, User.id == Review.user_id)
        .where(Review.product_id == str(product_id), Review.is_visible.is_(True))
        .order_by(Review.created_at.desc())
        .limit(100)
    ).all()
    return [
        ReviewOut(
            id=r.id,
            author=name,
            rating=r.rating,
            title=r.title,
            body=r.body,
            created_at=r.created_at,
        )
        for r, name in rows
    ]


@router.post("/shop/products/{product_id}/reviews", response_model=ReviewOut, status_code=201)
def add_review(product_id: UUID, body: ReviewIn, user=Depends(current_user), db=Depends(get_db)):
    product = listed(db, str(product_id))
    purchased = db.scalar(
        select(OrderItem.id)
        .join(Order, Order.id == OrderItem.order_id)
        .where(
            Order.user_id == user.id,
            OrderItem.product_id == product.id,
            Order.status == "delivered",
        )
        .limit(1)
    )
    if not purchased:
        raise HTTPException(403, "Reviews are available after your order is delivered")
    review = db.scalar(
        select(Review).where(Review.user_id == user.id, Review.product_id == product.id)
    )
    if review:
        review.rating, review.title, review.body = body.rating, body.title, body.body
    else:
        review = Review(user_id=user.id, product_id=product.id, **body.model_dump())
        db.add(review)
    db.commit()
    return ReviewOut(
        id=review.id,
        author=user.name,
        rating=review.rating,
        title=review.title,
        body=review.body,
        created_at=review.created_at,
    )


@router.get("/wishlist", response_model=list[ShopProduct])
def wishlist(user=Depends(current_user), db=Depends(get_db)):
    rows = db.scalars(
        select(Product)
        .join(Wishlist, Wishlist.product_id == Product.id)
        .where(
            Wishlist.user_id == user.id, Product.is_listed.is_(True), Product.is_archived.is_(False)
        )
    )
    return [product_view(db, p) for p in rows]


@router.put("/wishlist/{product_id}", response_model=MessageOut)
def save_wishlist(product_id: UUID, user=Depends(current_user), db=Depends(get_db)):
    listed(db, str(product_id))
    if db.get(Wishlist, (user.id, str(product_id))) is None:
        db.add(Wishlist(user_id=user.id, product_id=str(product_id)))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
    return MessageOut(message="Saved to wishlist")


@router.delete("/wishlist/{product_id}", response_model=MessageOut)
def remove_wishlist(product_id: UUID, user=Depends(current_user), db=Depends(get_db)):
    item = db.get(Wishlist, (user.id, str(product_id)))
    if item:
        db.delete(item)
        db.commit()
    return MessageOut(message="Removed from wishlist")


def seller_product(db, product_id: str, user, lock=False):
    stmt = select(Product).where(Product.id == product_id, Product.is_archived.is_(False))
    if user.role != "admin":
        stmt = stmt.where(Product.seller_id == user.id)
    product = db.scalar(stmt.with_for_update() if lock else stmt)
    if product is None:
        raise HTTPException(404, "Product not found")
    return product


def validate_listing(db, body: ListingIn, product=None):
    category = db.get(Category, body.category)
    if (category and not category.is_active) or (
        category is None and body.category not in DEFAULT_CATEGORIES
    ):
        raise HTTPException(422, "Choose an active category")
    if body.is_listed and (product is None or not product.images):
        raise HTTPException(422, "Upload at least one product photo before listing")


@router.get("/seller/products", response_model=list[ShopProduct])
def seller_products(user=Depends(seller_user), db=Depends(get_db)):
    stmt = select(Product).where(Product.is_archived.is_(False))
    if user.role != "admin":
        stmt = stmt.where(Product.seller_id == user.id)
    return [
        product_view(db, p, True)
        for p in db.scalars(stmt.order_by(Product.created_at.desc()).limit(200))
    ]


@router.post("/seller/products", response_model=ShopProduct, status_code=201)
def create_listing(body: ListingIn, user=Depends(seller_user), db=Depends(get_db)):
    validate_listing(db, body)
    product = Product(seller_id=user.id, **body.model_dump())
    db.add(product)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "SKU is already in use") from exc
    return product_view(db, product, True)


@router.put("/seller/products/{product_id}", response_model=ShopProduct)
def update_listing(
    product_id: UUID, body: ListingIn, user=Depends(seller_user), db=Depends(get_db)
):
    product = seller_product(db, str(product_id), user, True)
    validate_listing(db, body, product)
    for key, value in body.model_dump().items():
        setattr(product, key, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "SKU is already in use") from exc
    return product_view(db, product, True)


@router.delete("/seller/products/{product_id}", response_model=MessageOut)
def archive_listing(product_id: UUID, user=Depends(seller_user), db=Depends(get_db)):
    product = seller_product(db, str(product_id), user, True)
    product.is_listed, product.is_archived = False, True
    product.publish_status = "rejected"
    db.commit()
    return MessageOut(message="Product archived; historical orders are preserved")


@router.post("/seller/products/{product_id}/images", response_model=ShopProduct)
async def listing_images(
    product_id: UUID,
    files: list[UploadFile] = File(...),
    user=Depends(seller_user),
    db=Depends(get_db),
):
    product = seller_product(db, str(product_id), user, True)
    await upload_images(product_id, files, product.seller_id, db)
    db.refresh(product)
    return product_view(db, product, True)


@router.delete("/seller/products/{product_id}/images/{image_id}", response_model=ShopProduct)
def remove_image(product_id: UUID, image_id: UUID, user=Depends(seller_user), db=Depends(get_db)):
    product = seller_product(db, str(product_id), user, True)
    if product.publish_status == "generating":
        raise HTTPException(409, "Wait for generation to finish before changing photos")
    image = db.get(ProductImage, str(image_id))
    if image is None or image.product_id != product.id:
        raise HTTPException(404, "Photo not found")
    product.images.remove(image)
    product.publish_status = "draft"
    if not product.images:
        product.is_listed = False
    db.commit()
    return product_view(db, product, True)


@router.post("/seller/products/{product_id}/variants", response_model=VariantOut)
def save_variant(product_id: UUID, body: VariantIn, user=Depends(seller_user), db=Depends(get_db)):
    product = seller_product(db, str(product_id), user, True)
    variant = db.get(Variant, str(body.id)) if body.id else None
    if body.id and (variant is None or variant.product_id != product.id):
        raise HTTPException(404, "Option not found")
    if variant is None:
        variant = Variant(product_id=product.id)
        db.add(variant)
    for key, value in body.model_dump(exclude={"id"}).items():
        setattr(variant, key, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Option SKU is already in use") from exc
    return variant
