"""Explicit local-weight inference check. Not a test of product fidelity or try-on."""

import argparse
import io
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.common.config import Settings
from app.modules.quality.analysis import _foreground, _pixels
from app.modules.quality.optional_models import optional_quality_runtime
from PIL import Image, ImageOps


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=["sam2", "dinov2"], required=True)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--sam2-config", default="configs/sam2.1/sam2.1_hiera_t.yaml")
    parser.add_argument("--device", choices=["cpu", "auto", "cuda"], default="auto")
    args = parser.parse_args()
    try:
        import torch

        with Image.open(args.image) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
            image.thumbnail((384, 384))
            output = io.BytesIO()
            image.save(output, "PNG")
        data = output.getvalue()
        settings = Settings(
            ai_provider="mock",
            queue_mode="inline",
            environment="test",
            quality_device=args.device,
            quality_max_image_size=384,
            quality_enable_sam2=args.model == "sam2",
            quality_enable_dinov2=args.model == "dinov2",
            quality_sam2_config=args.sam2_config,
            quality_sam2_checkpoint=args.checkpoint if args.model == "sam2" else None,
            quality_dinov2_model_path=args.checkpoint
            if args.model == "dinov2"
            else None,
        )
        runtime = optional_quality_runtime(settings)
        assert runtime is not None
        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()
        started = time.perf_counter()
        if args.model == "sam2":
            pixels, width, _ = _pixels(data, 384)
            mask = _foreground(pixels, width)
            assert runtime.sam2_refiner is not None
            left, right, device = runtime.sam2_refiner(data, data, mask, mask, 384)
            assert len(left) == 384**2 and any(left) and any(right)
            detail = {"foreground_pixels": sum(left)}
        else:
            assert runtime.dinov2_scorer is not None
            score, device = runtime.dinov2_scorer(data, data, 384)
            assert score >= 0.95, "Identical-image sanity check failed"
            detail = {"identical_image_cosine": score}
        print(
            json.dumps(
                {
                    "status": "passed",
                    "model": args.model,
                    "device": device,
                    "elapsed_seconds": round(time.perf_counter() - started, 3),
                    "peak_cuda_mib": round(
                        torch.cuda.max_memory_allocated() / 1024**2, 2
                    )
                    if torch.cuda.is_available()
                    else 0,
                    "scope": "Local inference sanity only; no product fidelity certification",
                    **detail,
                },
                indent=2,
            )
        )
        return 0
    except Exception as exc:  # noqa: BLE001 - CLI reports optional-dependency/inference failures.
        print(
            json.dumps({"status": "unavailable_or_failed", "error": type(exc).__name__})
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
