from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException
from sqlalchemy import select

from app.common.auth import seller_id
from app.common.config import get_settings
from app.common.db import get_db
from app.common.models import GenerationJob, now
from app.common.schemas import JobOut
from app.common.views import job_out
from app.modules.catalog.routes import owned_product
from app.modules.generation.tasks import process_job, queue

router = APIRouter(tags=["Generation"])


@router.get("/products/{product_id}/generation-jobs", response_model=list[JobOut])
def list_jobs(product_id: UUID, owner: str = Depends(seller_id), db=Depends(get_db)):
    product = owned_product(db, product_id, owner)
    jobs = db.scalars(
        select(GenerationJob)
        .where(GenerationJob.product_id == product.id)
        .order_by(GenerationJob.created_at.desc())
        .limit(20)
    )
    return [job_out(job, owner) for job in jobs]


@router.post("/products/{product_id}/generation-jobs", response_model=JobOut, status_code=202)
def start_generation(
    product_id: UUID,
    background: BackgroundTasks,
    idempotency_key: str = Header(min_length=1, max_length=128),
    owner: str = Depends(seller_id),
    db=Depends(get_db),
):
    product = owned_product(db, product_id, owner, lock=True)
    existing = db.scalar(
        select(GenerationJob).where(
            GenerationJob.product_id == product.id, GenerationJob.idempotency_key == idempotency_key
        )
    )
    if existing:
        return job_out(existing, owner)
    if product.publish_status == "generating":
        raise HTTPException(409, "A generation is already active")
    settings = get_settings()
    if not settings.min_images <= len(product.images) <= settings.max_images:
        raise HTTPException(422, "Upload 2–5 images before generation")
    job = GenerationJob(product_id=product.id, idempotency_key=idempotency_key, provider="mock")
    product.publish_status = "generating"
    db.add(job)
    db.commit()
    db.refresh(job)
    try:
        if settings.queue_mode == "inline":
            background.add_task(process_job, job.id)
        else:
            queue().enqueue(process_job, job.id, job_id=job.id, result_ttl=86400)
    except Exception as exc:
        job.status, job.error_code, job.finished_at = "failed", "QUEUE_UNAVAILABLE", now()
        product.publish_status = "draft"
        db.commit()
        raise HTTPException(503, "Queue unavailable; retry with a new idempotency key") from exc
    return job_out(job, owner)


@router.get("/generation-jobs/{job_id}", response_model=JobOut)
def get_job(job_id: UUID, owner: str = Depends(seller_id), db=Depends(get_db)):
    job = db.get(GenerationJob, str(job_id))
    if job is None:
        raise HTTPException(404, "Job not found")
    owned_product(db, job.product_id, owner)
    return job_out(job, owner)
