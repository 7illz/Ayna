# Ayna Developer 2 verification - 2026-11-03

Executed on Windows 11 with Python 3.12.8, Node 24.14.1, 16 GB system RAM and an NVIDIA
GeForce RTX 4050 Laptop GPU. `nvidia-smi` reported driver 616.92, CUDA UMD 13.4 and
6,141 MiB total VRAM. PyTorch/SAM 2/DINOv2 weights were intentionally not installed in the
default application environment; optional model loaders remain disabled and CPU fallback is
the tested baseline. Docker was unavailable on PATH, so Compose validation was not run.

| Check | Result |
| --- | --- |
| `python scripts/check_gpu.py` | PASS; NVIDIA driver found, PyTorch absent, CPU path selected |
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
