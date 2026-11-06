import logging

from redis import Redis
from rq import Queue
from sqlalchemy import select, update

from app.common.config import get_settings
from app.common.db import SessionLocal
from app.common.models import GenerationJob, Product, now
from app.common.storage import get_storage
from app.modules.generation.meshy import MeshyProvider, ProviderError, select_views, validate_glb
from app.modules.generation.providers import MockProvider
from app.modules.quality.service import build_quality_artifacts

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

            def submitted(task_id: str):
                job.provenance = {"provider_task_id": task_id, "provider": "meshy"}
                db.commit()

            def progress(value: int):
                job.progress = value
                db.commit()

            if job.provider == "mock":
                result = MockProvider().generate([i.storage_key for i in product.images])
            elif job.provider == "meshy":
                result = MeshyProvider(submitted=submitted, progress=progress).generate(
                    [i.storage_key for i in select_views(product.images)]
                )
            else:
                raise ProviderError("PROVIDER_NOT_CONFIGURED")
            validate_glb(result.glb)
            filename = "dummy.glb" if job.provider == "mock" else "model.glb"
            key = f"models/{job.id}/{filename}"
            storage = get_storage()
            storage.put(key, result.glb, "model/gltf-binary")
            quality = build_quality_artifacts(
                product,
                job,
                model_glb=result.glb,
                # The mock octahedron is intentionally unrelated to uploaded photos.
                evaluate_rendered_views=job.provider != "mock",
            )
            render_keys: dict[str, str] = {}
            render_storage_failures: dict[str, str] = {}
            for view, png in quality.rendered_views.items():
                render_key = f"models/{job.id}/quality/{view}.png"
                try:
                    storage.put(render_key, png, "image/png")
                    render_keys[view] = render_key
                except Exception as exc:
                    logger.warning("Could not store %s quality render for job %s", view, job.id)
                    render_storage_failures[view] = exc.__class__.__name__
            job.model_key = key
            job.provenance = {
                **result.metadata,
                "input_image_ids": [image.id for image in product.images],
                "quality_rendering": quality.render_metadata,
                "quality_render_keys": render_keys,
                "quality_render_storage_failures": render_storage_failures,
            }
            job.status, job.progress, job.finished_at = "succeeded", 100, now()
            product.publish_status = "needs_review"
            # Deterministic screenshots are useful for inspection, but mock geometry has no
            # correspondence to the seller photos and therefore stays not_evaluated.
            db.add(quality.report)
            db.commit()
        except Exception as exc:
            # Do not log provider responses, URLs, uploaded photographs or credentials.
            logger.error("Generation failed for job %s (%s)", job_id, type(exc).__name__)
            db.rollback()
            db.execute(
                update(GenerationJob)
                .where(GenerationJob.id == job_id)
                .values(
                    status="failed",
                    error_code=str(exc) if isinstance(exc, ProviderError) else "GENERATION_FAILED",
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
