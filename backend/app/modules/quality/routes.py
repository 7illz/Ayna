from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.common.auth import seller_id
from app.common.db import get_db
from app.common.models import QualityReport, now
from app.common.schemas import ProductOut, QualityOut, ReviewIn
from app.common.views import product_out
from app.modules.catalog.routes import owned_product
from app.modules.generation.tasks import latest_job

router = APIRouter(tags=["Quality and review"])


@router.get("/products/{product_id}/quality", response_model=QualityOut)
def get_quality(product_id: UUID, owner: str = Depends(seller_id), db=Depends(get_db)):
    product = owned_product(db, product_id, owner)
    job = latest_job(db, product.id)
    report = db.get(QualityReport, job.id) if job else None
    if report is None:
        raise HTTPException(404, "Quality report is not ready")
    return report


@router.post("/products/{product_id}/review", response_model=ProductOut)
def review_product(
    product_id: UUID,
    body: ReviewIn,
    owner: str = Depends(seller_id),
    db=Depends(get_db),
):
    product = owned_product(db, product_id, owner, lock=True)
    job = latest_job(db, product.id)
    if product.publish_status not in {"needs_review", "approved", "rejected"}:
        raise HTTPException(409, "The current model is not ready for review")
    if not job or job.status != "succeeded" or not job.model_key:
        raise HTTPException(409, "A successful model is required for review")
    report = db.get(QualityReport, job.id)
    if report is None:
        raise HTTPException(409, "Quality report is not ready")
    product.publish_status = "approved" if body.decision == "approve" else "rejected"
    report.reviewed_by, report.reviewed_at = owner, now()
    report.notes = "Dummy fixture; fidelity not evaluated. Seller review: " + body.notes
    db.commit()
    return product_out(product)
