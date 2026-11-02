from app.common.config import get_settings
from app.common.models import GenerationJob, Product, QualityReport
from app.modules.quality.analysis import analyze_aligned_views


def build_quality_report(
    product: Product,
    job: GenerationJob,
    reference_images: dict[str, bytes] | None = None,
    rendered_views: dict[str, bytes] | None = None,
) -> QualityReport:
    result = analyze_aligned_views(
        reference_images or {},
        rendered_views or {},
        get_settings().quality_max_image_size,
    )
    return QualityReport(
        product_id=product.id,
        job_id=job.id,
        status=result.status,
        metrics=result.metrics,
        notes=result.notes,
        uncertain_views=result.uncertain_views,
    )
