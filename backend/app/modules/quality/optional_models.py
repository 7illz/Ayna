"""Optional pretrained-model runtime boundary; never downloads weights implicitly."""

import logging
from collections.abc import Callable

logger = logging.getLogger(__name__)


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
    operation: Callable[[str], T], requested: str = "auto"
) -> tuple[T, str]:
    """Retry CUDA out-of-memory once on CPU and release cached GPU allocations."""
    device = choose_device(requested)
    try:
        return operation(device), device
    except RuntimeError as exc:
        if device != "cuda" or "out of memory" not in str(exc).lower():
            raise
        logger.warning("Optional quality model exceeded GPU memory; retrying on CPU")
        try:
            import torch

            torch.cuda.empty_cache()
        except ImportError:
            pass
        return operation("cpu"), "cpu"


def load_dinov2_local(model_path: str, device: str):
    """Load an explicitly cached DINOv2 model; network downloads are disabled."""
    from transformers import AutoImageProcessor, AutoModel

    processor = AutoImageProcessor.from_pretrained(model_path, local_files_only=True)
    model = AutoModel.from_pretrained(model_path, local_files_only=True).to(device).eval()
    return processor, model


def load_sam2_local(config_path: str, checkpoint_path: str, device: str):
    """Load SAM 2 from an explicit Tiny/Small checkpoint path."""
    from sam2.build_sam import build_sam2

    return build_sam2(config_path, checkpoint_path, device=device, apply_postprocessing=True)
