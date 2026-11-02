"""Interpretable, CPU-safe image checks for defensibly aligned product views.

The engine deliberately refuses to compare differently labelled or unknown camera views.
It is not an identity verifier and its signals must remain advisory to the seller.
"""

from dataclasses import dataclass
from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError

KNOWN_VIEWS = ("front", "left", "right", "side", "back")


@dataclass(frozen=True)
class AnalysisResult:
    status: str
    metrics: dict
    notes: str
    uncertain_views: list[str]


def _pixels(data: bytes, size: int) -> tuple[list[tuple[int, int, int]], int, int]:
    with Image.open(BytesIO(data)) as source:
        image = ImageOps.fit(source.convert("RGB"), (size, size))
        flattened = getattr(image, "get_flattened_data", None)
        pixels = flattened() if flattened else image.getdata()
        return list(pixels), image.width, image.height


def _foreground(pixels: list[tuple[int, int, int]], width: int) -> list[bool]:
    corners = [pixels[0], pixels[width - 1], pixels[-width], pixels[-1]]
    background = tuple(sum(value[channel] for value in corners) / 4 for channel in range(3))
    return [max(abs(pixel[i] - background[i]) for i in range(3)) >= 28 for pixel in pixels]


def _mean_color(pixels: list[tuple[int, int, int]], mask: list[bool]) -> tuple[float, float, float]:
    selected = [pixel for pixel, keep in zip(pixels, mask, strict=True) if keep] or pixels
    channels = [sum(pixel[i] for pixel in selected) / len(selected) for i in range(3)]
    return channels[0], channels[1], channels[2]


def _signals(reference: bytes, render: bytes, size: int) -> dict[str, float]:
    ref, width, _ = _pixels(reference, size)
    candidate, _, _ = _pixels(render, size)
    ref_mask = _foreground(ref, width)
    candidate_mask = _foreground(candidate, width)
    intersection = sum(a and b for a, b in zip(ref_mask, candidate_mask, strict=True))
    union = sum(a or b for a, b in zip(ref_mask, candidate_mask, strict=True))
    silhouette_iou = intersection / union if union else 1.0
    ref_color, candidate_color = _mean_color(ref, ref_mask), _mean_color(candidate, candidate_mask)
    color_distance = sum(abs(a - b) for a, b in zip(ref_color, candidate_color, strict=True)) / (
        3 * 255
    )
    pixel_difference = sum(
        sum(abs(a - b) for a, b in zip(left, right, strict=True))
        for left, right in zip(ref, candidate, strict=True)
    ) / (len(ref) * 3 * 255)
    return {
        "silhouette_iou": round(silhouette_iou, 4),
        "mean_color_distance": round(color_distance, 4),
        "pixel_difference": round(pixel_difference, 4),
    }


def analyze_aligned_views(
    references: dict[str, bytes], renders: dict[str, bytes], max_image_size: int = 384
) -> AnalysisResult:
    """Compare exact known-view matches only; unknown alignment yields no numeric scores."""
    matched = sorted(set(references) & set(renders) & set(KNOWN_VIEWS))
    uncertain = sorted(
        {view for view in references if view not in matched}
        | {view for view in renders if view not in matched}
    )
    if not matched:
        return AnalysisResult(
            status="not_evaluated",
            metrics={},
            notes=(
                "No reference/render camera views could be defensibly aligned; "
                "seller review required."
            ),
            uncertain_views=uncertain or ["all views - camera alignment unavailable"],
        )

    view_metrics: dict[str, dict[str, float]] = {}
    flags: list[str] = []
    invalid: list[str] = []
    size = max(128, min(max_image_size, 1024))
    for view in matched:
        try:
            signals = _signals(references[view], renders[view], size)
        except (UnidentifiedImageError, OSError, ValueError):
            invalid.append(view)
            continue
        view_metrics[view] = signals
        if signals["silhouette_iou"] < 0.65:
            flags.append(f"{view}: likely geometry/silhouette mismatch")
        if signals["mean_color_distance"] > 0.18:
            flags.append(f"{view}: likely color mismatch")
        if signals["pixel_difference"] > 0.35:
            flags.append(f"{view}: possible texture/logo/detail mismatch")

    uncertain.extend(f"{view} - unreadable comparison image" for view in invalid)
    if not view_metrics:
        return AnalysisResult(
            status="failed",
            metrics={},
            notes="Aligned comparison images could not be decoded; no fidelity score was produced.",
            uncertain_views=uncertain,
        )
    status = "pass" if not flags and not uncertain else "needs_review"
    return AnalysisResult(
        status=status,
        metrics={
            "engine": "cpu-interpretable-v1",
            "aligned_views": list(view_metrics),
            "views": view_metrics,
            "flags": flags,
        },
        notes=(
            "Advisory aligned-view checks only; they cannot certify product identity "
            "or unseen details."
        ),
        uncertain_views=uncertain,
    )
