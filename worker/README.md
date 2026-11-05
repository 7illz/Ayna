# Ayna worker

The shared CPU-safe RQ worker lives in `backend/app/worker.py` and uses the API image.
`backend/app/modules/quality/analysis.py` provides the default dependency-light fidelity
signals. It only scores exact camera-label matches and returns `not_evaluated` when the
views cannot be aligned.

`backend/app/modules/quality/rendering.py` provides deterministic CPU-only front, left,
right and back PNG inspection views for embedded, uncompressed GLB triangle meshes. It runs
inside the existing generation worker and requires no package beyond the backend's pinned
Pillow dependency. Render failures are isolated from generation and become honest
`not_evaluated`/`needs_review` outcomes rather than fabricated scores. See
`docs/DEV2_QUALITY_STOREFRONT.md` for supported GLB features, limits and test commands.

Optional pretrained SAM 2 Tiny/Small and DINOv2 Small adapters are isolated in
`backend/app/modules/quality/optional_models.py`. They are disabled by default and never
download weights at runtime. SAM 2 only refines foreground masks; DINOv2 runs only after
camera-label alignment and emits an advisory similarity that is explicitly not identity
proof. Missing optional dependencies or local weights preserve the deterministic baseline.
Keep checkpoints outside the repository/model cache, resize inputs to 384 px, use inference
mode with batch size one, and run `scripts/check_gpu.py` before enabling `QUALITY_DEVICE=auto`.
CUDA OOM is retried exactly once on CPU. The normal API image
contains no CUDA, PyTorch, SAM 2, DINOv2, or model-weight dependency, so Intel Iris Xe and
CPU-only Docker remain supported.

See `docs/DEV2_QUALITY_STOREFRONT.md` for the opt-in environment setup and safety limits.
Pinned optional runtime packages are in `worker/requirements-vision.txt`; they are excluded
from the API/worker Docker image and must be installed only in a separate lab environment.
