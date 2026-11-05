from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select

from app.common.db import get_db
from app.common.models import Product, ProductImage
from app.common.schemas import PublicImage, PublicProduct
from app.common.storage import get_storage
from app.modules.generation.providers import DISCLOSURE
from app.modules.generation.tasks import latest_job

router = APIRouter(tags=["Public storefront"])


def stored_asset(key: str, media_type: str) -> Response:
    try:
        data = get_storage().get(key)
    except Exception as exc:
        raise HTTPException(404, "Asset unavailable") from exc
    return Response(data, media_type=media_type, headers={"Cache-Control": "no-store"})


def approved(db, product_id: str) -> Product:
    product = db.get(Product, product_id)
    if product is None or product.publish_status != "approved":
        raise HTTPException(404, "Product not found")
    job = latest_job(db, product.id)
    if not job or job.status != "succeeded" or not job.model_key:
        raise HTTPException(404, "Product not found")
    return product


def public_product(db, product: Product) -> PublicProduct:
    job = latest_job(db, product.id)
    return PublicProduct(
        id=UUID(product.id),
        name=product.name,
        category=product.category,
        description=product.description,
        images=[
            PublicImage(
                id=UUID(i.id),
                url=f"/api/v1/store/products/{product.id}/images/{i.id}",
                view_tag=i.view_tag,
            )
            for i in product.images
        ],
        model_asset_url=f"/api/v1/store/products/{product.id}/model"
        if job and job.status == "succeeded" and job.model_key
        else None,
        disclosure=DISCLOSURE,
    )


@router.get("/store/products", response_model=list[PublicProduct])
def store_products(db=Depends(get_db)):
    products = db.scalars(select(Product).where(Product.publish_status == "approved").limit(100))
    published = []
    for product in products:
        job = latest_job(db, product.id)
        if job and job.status == "succeeded" and job.model_key:
            published.append(public_product(db, product))
    return published


@router.get("/store/products/{product_id}", response_model=PublicProduct)
def store_product(product_id: UUID, db=Depends(get_db)):
    return public_product(db, approved(db, str(product_id)))


@router.get("/store/products/{product_id}/model")
def store_model(product_id: UUID, db=Depends(get_db)):
    approved(db, str(product_id))
    job = latest_job(db, str(product_id))
    if not job or not job.model_key or job.status != "succeeded":
        raise HTTPException(404, "Model unavailable")
    return stored_asset(job.model_key, "model/gltf-binary")


@router.get("/store/products/{product_id}/images/{image_id}")
def store_image(product_id: UUID, image_id: UUID, db=Depends(get_db)):
    approved(db, str(product_id))
    image = db.get(ProductImage, str(image_id))
    if image is None or image.product_id != str(product_id):
        raise HTTPException(404, "Image unavailable")
    return stored_asset(image.storage_key, "image/png")
