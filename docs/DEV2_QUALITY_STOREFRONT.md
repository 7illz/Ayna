# Ayna quality and storefront implementation

The default Ayna quality engine is CPU-safe and has no CUDA dependency. It calculates
interpretable silhouette, mean-color and pixel-difference signals only when a seller photo
and a generated render carry the same known camera label. Unknown or unmatched views return
`not_evaluated`; the engine never turns missing alignment into a numeric confidence score.
Mock generation has no camera-labelled renders, so seller inspection remains mandatory.

## Optional RTX 4050 lab

Run `python scripts/check_gpu.py` and `nvidia-smi` first. Install a CUDA-enabled PyTorch build
that matches the current NVIDIA driver in a separate virtual environment, then install the
official SAM 2 package and/or Transformers from their official projects. Use only SAM 2
Hiera Tiny/Small and DINOv2 Small checkpoints. Store weights outside Git and configure local
paths explicitly; Ayna never downloads model weights at API startup.

The tested isolated setup is reproducible with:

```powershell
python -m venv .venv-vision
.\.venv-vision\Scripts\python -m pip install -r worker\requirements-vision.txt
.\.venv-vision\Scripts\python scripts\check_vision_runtime.py
```

Recommended settings for 6 GB VRAM are batch size one, 384 px longest edge, inference mode,
and no concurrent local model jobs. Start with:

```powershell
$env:QUALITY_DEVICE='auto'
$env:QUALITY_MAX_IMAGE_SIZE='384'
$env:QUALITY_ENABLE_SAM2='true'
$env:QUALITY_SAM2_CHECKPOINT='D:\models\sam2.1_hiera_tiny.pt'
python scripts/check_gpu.py
```

For an optional locally cached DINOv2 Small model, also set
`QUALITY_ENABLE_DINOV2=true` and `QUALITY_DINOV2_MODEL_PATH` to that directory.

`optional_models.run_with_cpu_fallback` retries a CUDA out-of-memory failure once on CPU.
If PyTorch or a checkpoint is absent, keep both optional flags false. The normal Compose
stack must remain `QUALITY_DEVICE=cpu`; this is the Intel Iris Xe-compatible path.

The optional DINOv2 loader uses `local_files_only=True`. Embeddings may add a correspondence
signal after camera alignment, but they do not certify product identity. SAM 2 masks are an
optional refinement to the deterministic corner-background mask; they do not auto-correct
the generated model.

## Review and publication

Every approve/reject action is owner-authorized and appended to `review_audits`. Approval
requires the latest successful model and a non-failed quality report. Public list, detail,
image and model routes re-check current approval; corruption or a missing current model is
treated as unpublished. The browser keeps original photographs visible and falls back to
them when WebGL or the GLB fails.
