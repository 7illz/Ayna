# Ayna worker

The shared CPU-safe RQ worker lives in `backend/app/worker.py` and uses the API image.
`backend/app/modules/quality/analysis.py` provides the default dependency-light fidelity
signals. It only scores exact camera-label matches and returns `not_evaluated` when the
views cannot be aligned.

Optional pretrained SAM 2 Tiny/Small and DINOv2 Small adapters are isolated in
`backend/app/modules/quality/optional_models.py`. They are disabled by default and never
download weights at runtime. Keep checkpoints outside the repository/model cache, resize
inputs to 384 px, use inference mode with batch size one, and run `scripts/check_gpu.py`
before enabling `QUALITY_DEVICE=auto`. CUDA OOM is retried on CPU. The normal API image
contains no CUDA, PyTorch, SAM 2, DINOv2, or model-weight dependency, so Intel Iris Xe and
CPU-only Docker remain supported.

See `docs/DEV2_QUALITY_STOREFRONT.md` for the opt-in environment setup and safety limits.
