import io
import sys
from types import SimpleNamespace

from PIL import Image, ImageDraw

from app.modules.quality.analysis import analyze_aligned_views
from app.modules.quality.optional_models import choose_device, run_with_cpu_fallback


def image(color: str, shape: str = "box") -> bytes:
    canvas = Image.new("RGB", (96, 96), "white")
    draw = ImageDraw.Draw(canvas)
    if shape == "box":
        draw.rectangle((20, 20, 76, 76), fill=color)
    else:
        draw.ellipse((32, 12, 64, 84), fill=color)
    output = io.BytesIO()
    canvas.save(output, "PNG")
    return output.getvalue()


def test_missing_camera_match_produces_no_fabricated_metrics():
    result = analyze_aligned_views({"front": image("red")}, {"back": image("red")})
    assert result.status == "not_evaluated"
    assert result.metrics == {}
    assert result.uncertain_views == ["back", "front"]


def test_aligned_identical_view_passes_interpretable_checks():
    front = image("#315f9b")
    result = analyze_aligned_views({"front": front}, {"front": front}, 128)
    assert result.status == "pass"
    assert result.metrics["aligned_views"] == ["front"]
    assert result.metrics["views"]["front"]["silhouette_iou"] == 1.0
    assert result.metrics["flags"] == []


def test_aligned_mismatch_is_flagged_for_human_review():
    result = analyze_aligned_views(
        {"front": image("red", "box")}, {"front": image("blue", "ellipse")}, 128
    )
    assert result.status == "needs_review"
    assert any("geometry" in flag for flag in result.metrics["flags"])
    assert any("color" in flag for flag in result.metrics["flags"])


def test_optional_runtime_is_cpu_safe_and_retries_cuda_oom(monkeypatch):
    assert choose_device("cpu") == "cpu"
    cuda = SimpleNamespace(is_available=lambda: True, empty_cache=lambda: None)
    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(cuda=cuda))
    calls = []

    def operation(device):
        calls.append(device)
        if device == "cuda":
            raise RuntimeError("CUDA out of memory")
        return "ok"

    assert run_with_cpu_fallback(operation, "auto") == ("ok", "cpu")
    assert calls == ["cuda", "cpu"]
