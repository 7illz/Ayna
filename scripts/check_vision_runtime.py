"""Bounded optional CUDA smoke check; this does not load or download model weights."""

import json
import time


def main() -> int:
    try:
        import cv2
        import sam2  # noqa: F401
        import torch
        import transformers
    except ImportError as exc:
        print(json.dumps({"status": "unavailable", "detail": str(exc)}, indent=2))
        return 1

    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cuda":
        torch.cuda.reset_peak_memory_stats()
    started = time.perf_counter()
    with torch.inference_mode():
        image = torch.rand((1, 3, 384, 384), device=device)
        kernel = torch.rand((32, 3, 3, 3), device=device)
        result = torch.nn.functional.conv2d(image, kernel, padding=1)
        result.mean().item()
    if device == "cuda":
        torch.cuda.synchronize()
    report = {
        "status": "ok",
        "device": device,
        "gpu": torch.cuda.get_device_name(0) if device == "cuda" else None,
        "torch": torch.__version__,
        "cuda_runtime": torch.version.cuda,
        "opencv": cv2.__version__,
        "transformers": transformers.__version__,
        "sam2_import": True,
        "input_size": [1, 3, 384, 384],
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
        "peak_mib": (
            round(torch.cuda.max_memory_allocated() / 1024**2, 2)
            if device == "cuda"
            else 0
        ),
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
