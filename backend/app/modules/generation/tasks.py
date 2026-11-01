import logging

from redis import Redis
from rq import Queue
from sqlalchemy import select, update

from app.common.config import get_settings
from app.common.db import SessionLocal
from app.common.models import GenerationJob, Product, QualityReport, now
from app.common.storage import get_storage
from app.modules.generation.providers import MockProvider

logger = logging.getLogger(__name__)


def queue() -> Queue:
    return Queue("ayna", connection=Redis.from_url(get_settings().redis_url), default_timeout=120)


def process_job(job_id: str) -> None:
    """Claim once, persist a deterministic artifact, then create an honest quality report."""
    with SessionLocal() as db:
        claimed = db.scalar(
            update(GenerationJob)
            .where(GenerationJob.id == job_id, GenerationJob.status == "queued")
            .values(status="processing", progress=15)
            .returning(GenerationJob.id)
        )
        db.commit()
        if claimed is None:
            return
        job = db.get(GenerationJob, job_id)
        if job is None:
            return
        try:
            product = db.get(Product, job.product_id)
            if product is None:
                raise ValueError("Product missing")
            result = MockProvider().generate([i.storage_key for i in product.images])
            if not result.glb.startswith(b"glTF"):
                raise ValueError("Invalid model")
            key = f"models/{job.id}/dummy.glb"
            get_storage().put(key, result.glb, "model/gltf-binary")
            job.model_key = key
            job.provenance = result.metadata
            job.status, job.progress, job.finished_at = "succeeded", 100, now()
            product.publish_status = "needs_review"
            db.add(
                QualityReport(
                    product_id=product.id,
                    job_id=job.id,
                    status="not_evaluated",
                    metrics={},
                    notes=(
                        "Dummy fixture: photo fidelity cannot be evaluated. Seller review required."
                    ),
                    uncertain_views=["all views — dummy geometry; no camera alignment"],
                )
            )
            db.commit()
        except Exception:
            logger.exception("Mock generation failed for job %s", job_id)
            db.rollback()
            db.execute(
                update(GenerationJob)
                .where(GenerationJob.id == job_id)
                .values(
                    status="failed",
                    error_code="GENERATION_FAILED",
                    finished_at=now(),
                    model_key=None,
                )
            )
            db.execute(
                update(Product).where(Product.id == job.product_id).values(publish_status="draft")
            )
            db.commit()


def latest_job(db, product_id: str):
    return db.scalar(
        select(GenerationJob)
        .where(GenerationJob.product_id == product_id)
        .order_by(GenerationJob.created_at.desc())
        .limit(1)
    )
