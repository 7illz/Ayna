# Ayna Developer 2 verification - 2026-11-03

Executed on Windows 11 with Python 3.12.8, Node 24.14.1, 16 GB system RAM and an NVIDIA
GeForce RTX 4050 Laptop GPU. `nvidia-smi` reported driver 616.92, CUDA UMD 13.4 and
6,141 MiB total VRAM. The default application remains CPU-only. A separate ignored vision
environment installed CUDA PyTorch 2.11.0+cu128, official SAM 2 commit `2b90b9f5`,
Transformers 5.22.1 and OpenCV 5.0.0. No SAM 2 or DINOv2 model weights were downloaded.
Docker was unavailable on PATH, so Compose validation was not run.

| Check | Result |
| --- | --- |
| `.venv-vision` `scripts/check_gpu.py` | PASS; RTX 4050 and CUDA available |
| `.venv-vision` `scripts/check_vision_runtime.py` | PASS; 384 px CUDA operation, 20.85 MiB peak VRAM |
| `pytest -q` | PASS: 22 tests |
| `ruff check .` | PASS |
| `ruff format --check .` | PASS: 36 files |
| `mypy app` | PASS: 25 source files |
| `alembic upgrade head` + `alembic check` | PASS; no migration drift |
| `npm run lint` | PASS |
| `npm run typecheck` | PASS |
| `npm run test -- --run` | PASS: 7 tests across 3 files |
| `npm run build` | PASS; Vite production build |

Backend coverage includes review ownership/state transitions, append-only audit decisions,
approved-only publication guards, camera-mismatch `not_evaluated`, aligned signal checks,
mismatch flags and simulated CUDA OOM retry to CPU. Frontend coverage includes seller review
uncertainty/rejection reasons, approved public detail/gallery integration, accessible 3D
controls, loading state and photograph fallback.

The existing Starlette/httpx deprecation warning remains. Vite reports the lazy Three.js
viewer chunk at about 1 MB (about 271 kB gzip). npm reports 14 moderate development-tooling
advisories; no forced breaking dependency upgrade was applied.
