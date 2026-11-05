"""Opt-in local pretrained-model boundary; no code path downloads model weights."""

from __future__ import annotations

import gc
import io
import logging
import math
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PIL import Image, ImageOps

if TYPE_CHECKING:
    from app.common.config import Settings

logger = logging.getLogger(__name__)

SAM2_LOCAL_CONFIGS = frozenset(
    {
        "configs/sam2/sam2_hiera_t.yaml",
        "configs/sam2/sam2_hiera_s.yaml",
        "configs/sam2.1/sam2.1_hiera_t.yaml",
        "configs/sam2.1/sam2.1_hiera_s.yaml",
    }
)

MaskPairRefiner = Callable[
    [bytes, bytes, list[bool], list[bool], int],
    tuple[list[bool], list[bool], str],
]
CorrespondenceScorer = Callable[[bytes, bytes, int], tuple[float, str]]


@dataclass(frozen=True)
class OptionalQualityRuntime:
    """Optional callables injected after deterministic camera alignment."""

    sam2_refiner: MaskPairRefiner | None = None
    dinov2_scorer: CorrespondenceScorer | None = None


class OptionalModelUnavailable(RuntimeError):
    """An explicitly enabled local model cannot be used safely."""


def choose_device(requested: str) -> str:
    if requested == "cpu":
        return "cpu"
    try:
        import torch

        if torch.cuda.is_available():
            return "cuda"
    except ImportError:
        pass
    if requested == "cuda":
        logger.warning("CUDA was requested but PyTorch CUDA is unavailable; using CPU")
    return "cpu"


def run_with_cpu_fallback[T](
    operation: Callable[[str], T],
    requested: str = "auto",
    *,
    on_cuda_oom: Callable[[], None] | None = None,
) -> tuple[T, str]:
    """Retry a CUDA out-of-memory failure exactly once on CPU."""
    device = choose_device(requested)
    try:
        return operation(device), device
    except RuntimeError as exc:
        if device != "cuda" or "out of memory" not in str(exc).lower():
            raise

    logger.warning("Optional quality model exceeded GPU memory; retrying once on CPU")
    if on_cuda_oom is not None:
        on_cuda_oom()
    gc.collect()
    try:
        import torch

        torch.cuda.empty_cache()
    except ImportError:
        pass
    return operation("cpu"), "cpu"


def _existing_local_path(
    raw_path: str,
    label: str,
    *,
    file_only: bool = False,
    directory_only: bool = False,
) -> Path:
    path = Path(raw_path).expanduser()
    if (
        not path.exists()
        or (file_only and not path.is_file())
        or (directory_only and not path.is_dir())
    ):
        raise OptionalModelUnavailable(f"Configured local {label} path is unavailable")
    return path.resolve()


def load_dinov2_local(model_path: str, device: str):
    """Load an explicitly configured local DINOv2 directory with network access disabled."""
    local_path = _existing_local_path(model_path, "DINOv2 model", directory_only=True)
    from transformers import AutoImageProcessor, AutoModel

    options = {"local_files_only": True, "trust_remote_code": False}
    processor = AutoImageProcessor.from_pretrained(str(local_path), **options)
    model = AutoModel.from_pretrained(str(local_path), **options).to(device).eval()
    return processor, model


def load_sam2_local(config_path: str, checkpoint_path: str, device: str):
    """Load a local SAM 2 Tiny/Small checkpoint; remote model identifiers are rejected."""
    if config_path not in SAM2_LOCAL_CONFIGS:
        raise OptionalModelUnavailable(
            "SAM 2 config must be an explicitly configured package-local Tiny/Small config"
        )
    checkpoint = _existing_local_path(checkpoint_path, "SAM 2 checkpoint", file_only=True)
    from sam2.build_sam import build_sam2

    return build_sam2(
        config_path,
        str(checkpoint),
        device=device,
        apply_postprocessing=True,
    )


@lru_cache(maxsize=4)
def _cached_sam2_model(config_path: str, checkpoint_path: str, device: str):
    return load_sam2_local(config_path, checkpoint_path, device)


@lru_cache(maxsize=4)
def _cached_dinov2(model_path: str, device: str):
    return load_dinov2_local(model_path, device)


def _fitted_image(data: bytes, size: int) -> Image.Image:
    with Image.open(io.BytesIO(data)) as source:
        return ImageOps.fit(source.convert("RGB"), (size, size))


def _mask_box(mask: list[bool], size: int) -> list[float]:
    points = [index for index, foreground in enumerate(mask) if foreground]
    if not points:
        raise OptionalModelUnavailable("The deterministic foreground mask is empty")
    xs = [index % size for index in points]
    ys = [index // size for index in points]
    return [float(min(xs)), float(min(ys)), float(max(xs)), float(max(ys))]


def _sam2_mask(model: Any, data: bytes, baseline: list[bool], size: int) -> list[bool]:
    from sam2.sam2_image_predictor import SAM2ImagePredictor

    predictor = SAM2ImagePredictor(model)
    predictor.set_image(_fitted_image(data, size))
    masks, scores, _ = predictor.predict(
        box=_mask_box(baseline, size),
        multimask_output=True,
    )
    best = int(scores.argmax())
    refined = [bool(value) for value in masks[best].reshape(-1).tolist()]
    if len(refined) != size * size or not any(refined):
        raise OptionalModelUnavailable("SAM 2 returned an invalid foreground mask")
    return refined


def _sam2_pair_refiner(
    config_path: str,
    checkpoint_path: str,
    requested_device: str,
) -> MaskPairRefiner:
    def refine(
        reference: bytes,
        render: bytes,
        reference_mask: list[bool],
        render_mask: list[bool],
        size: int,
    ) -> tuple[list[bool], list[bool], str]:
        def operation(device: str) -> tuple[list[bool], list[bool]]:
            model = _cached_sam2_model(config_path, checkpoint_path, device)
            return (
                _sam2_mask(model, reference, reference_mask, size),
                _sam2_mask(model, render, render_mask, size),
            )

        masks, device = run_with_cpu_fallback(
            operation,
            requested_device,
            on_cuda_oom=_cached_sam2_model.cache_clear,
        )
        return masks[0], masks[1], device

    return refine


def _dinov2_pair_score(model_path: str, requested_device: str) -> CorrespondenceScorer:
    def score(reference: bytes, render: bytes, size: int) -> tuple[float, str]:
        def operation(device: str) -> float:
            import torch

            processor, model = _cached_dinov2(model_path, device)
            inputs = processor(
                images=[_fitted_image(reference, size), _fitted_image(render, size)],
                return_tensors="pt",
            )
            device_inputs = {name: value.to(device) for name, value in inputs.items()}
            with torch.inference_mode():
                output = model(**device_inputs)
            pooled = getattr(output, "pooler_output", None)
            if pooled is None:
                pooled = output.last_hidden_state[:, 0, :]
            similarity = torch.nn.functional.cosine_similarity(
                pooled[0].float(), pooled[1].float(), dim=0
            ).item()
            if not math.isfinite(similarity):
                raise OptionalModelUnavailable("DINOv2 returned a non-finite similarity")
            return max(-1.0, min(1.0, float(similarity)))

        similarity, device = run_with_cpu_fallback(
            operation,
            requested_device,
            on_cuda_oom=_cached_dinov2.cache_clear,
        )
        return similarity, device

    return score


def optional_quality_runtime(settings: Settings) -> OptionalQualityRuntime | None:
    """Create lazy local-model callables; disabled settings import no optional dependency."""
    if not settings.quality_enable_sam2 and not settings.quality_enable_dinov2:
        return None

    sam2_refiner: MaskPairRefiner | None = None
    if settings.quality_enable_sam2:
        if not settings.quality_sam2_config or not settings.quality_sam2_checkpoint:
            raise OptionalModelUnavailable("SAM 2 local paths are not configured")
        sam2_refiner = _sam2_pair_refiner(
            settings.quality_sam2_config,
            settings.quality_sam2_checkpoint,
            settings.quality_device,
        )

    dinov2_scorer: CorrespondenceScorer | None = None
    if settings.quality_enable_dinov2:
        if not settings.quality_dinov2_model_path:
            raise OptionalModelUnavailable("DINOv2 local path is not configured")
        dinov2_scorer = _dinov2_pair_score(
            settings.quality_dinov2_model_path,
            settings.quality_device,
        )

    return OptionalQualityRuntime(sam2_refiner, dinov2_scorer)
