from uuid import UUID

from app.common.models import GenerationJob, Product
from app.common.schemas import JobOut, JobStatus, ProductImageOut, ProductOut, PublishStatus
from app.common.storage import asset_url
from app.modules.generation.providers import disclosure


def product_out(product: Product) -> ProductOut:
    return ProductOut(
        id=UUID(product.id),
        seller_id=UUID(product.seller_id),
        name=product.name,
        category=product.category,
        description=product.description,
        publish_status=PublishStatus(product.publish_status),
        created_at=product.created_at,
        updated_at=product.updated_at,
        images=[
            ProductImageOut(
                id=UUID(i.id),
                product_id=UUID(i.product_id),
                storage_key=i.storage_key,
                view_tag=i.view_tag,
                sort_order=i.sort_order,
                url=asset_url("image", i.id, product.seller_id),
            )
            for i in product.images
        ],
    )


def job_out(job: GenerationJob, owner: str) -> JobOut:
    return JobOut(
        id=UUID(job.id),
        product_id=UUID(job.product_id),
        provider=job.provider,
        status=JobStatus(job.status),
        progress=job.progress,
        created_at=job.created_at,
        finished_at=job.finished_at,
        error_code=job.error_code,
        model_asset_url=asset_url("model", job.id, owner) if job.model_key else None,
        preview_asset_urls=[
            asset_url(f"render-{view}", job.id, owner)
            for view in ("front", "left", "right", "back")
            if view in job.provenance.get("quality_render_keys", {}) and job.status == "succeeded"
        ],
        disclosure=disclosure(job.provider),
    )
