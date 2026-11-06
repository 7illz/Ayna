import io
import warnings
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.auth import seller_id
from app.common.config import get_settings
from app.common.db import get_db
from app.common.models import Product, ProductImage, new_id
from app.common.schemas import ProductCreate, ProductOut
from app.common.storage import get_storage
from app.common.views import product_out

router = APIRouter(tags=["Seller catalog"])


def owned_product(db: Session, product_id: UUID | str, owner: str, lock=False) -> Product:
    stmt = select(Product).where(Product.id == str(product_id), Product.seller_id == owner)
    if lock:
        stmt = stmt.with_for_update()
    product = db.scalar(stmt)
    if product is None:
        raise HTTPException(404, "Product not found")
    return product


@router.post("/products", response_model=ProductOut, status_code=201)
def create_product(body: ProductCreate, owner: str = Depends(seller_id), db=Depends(get_db)):
    product = Product(seller_id=owner, **body.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product_out(product)


@router.get("/products", response_model=list[ProductOut])
def list_products(owner: str = Depends(seller_id), db=Depends(get_db)):
    products = db.scalars(
        select(Product)
        .where(Product.seller_id == owner)
        .order_by(Product.created_at.desc())
        .limit(100)
    ).all()
    return [product_out(p) for p in products]


@router.get("/products/{product_id}", response_model=ProductOut)
def get_product(product_id: UUID, owner: str = Depends(seller_id), db=Depends(get_db)):
    return product_out(owned_product(db, product_id, owner))


def sanitize_image(data: bytes, content_type: str | None) -> bytes:
    settings = get_settings()
    if len(data) > settings.max_image_bytes:
        raise HTTPException(413, "Image exceeds the byte limit")
    formats = {"image/png": "PNG", "image/jpeg": "JPEG", "image/webp": "WEBP"}
    if content_type not in formats:
        raise HTTPException(415, "Use JPEG, PNG, or WebP images")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                if image.format != formats[content_type]:
                    raise HTTPException(415, "Image signature does not match its MIME type")
                if image.width * image.height > settings.max_image_pixels:
                    raise HTTPException(413, "Image exceeds the pixel limit")
                image.verify()
            with Image.open(io.BytesIO(data)) as image:
                clean = ImageOps.exif_transpose(image).convert("RGB")
                clean.thumbnail((1600, 1600))
                # Fresh pixel buffer drops all metadata, including EXIF/XMP/ICC.
                derivative = Image.frombytes("RGB", clean.size, clean.tobytes())
                output = io.BytesIO()
                derivative.save(output, "PNG")
                return output.getvalue()
    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as exc:
        raise HTTPException(422, "Invalid or unsafe image") from exc


@router.post("/products/{product_id}/images", response_model=ProductOut, status_code=201)
async def upload_images(
    product_id: UUID,
    files: list[UploadFile] = File(...),
    owner: str = Depends(seller_id),
    db=Depends(get_db),
):
    product = owned_product(db, product_id, owner, lock=True)
    if product.publish_status == "generating":
        raise HTTPException(409, "Wait for the current generation to finish")
    settings = get_settings()
    if not files or len(product.images) + len(files) > settings.max_images:
        raise HTTPException(422, f"A product may have at most {settings.max_images} images")
    validated = []
    for file in files:
        raw = await file.read(settings.max_image_bytes + 1)
        validated.append((raw, sanitize_image(raw, file.content_type), file.content_type))
        await file.close()
    storage = get_storage()
    for raw, derivative, content_type in validated:
        image_id = new_id()
        prefix = f"products/{product.id}/{image_id}"
        storage.put(f"{prefix}/original", raw, content_type or "application/octet-stream")
        storage.put(f"{prefix}/photo.png", derivative, "image/png")
        product.images.append(
            ProductImage(
                id=image_id,
                storage_key=f"{prefix}/photo.png",
                original_key=f"{prefix}/original",
                view_tag="front" if not product.images else "unspecified",
                sort_order=len(product.images),
            )
        )
    product.publish_status = "draft"
    db.commit()
    db.refresh(product)
    return product_out(product)
