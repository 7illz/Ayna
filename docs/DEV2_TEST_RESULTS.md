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

## CPU GLB renderer verification - 2026-11-06

The quality pipeline now renders deterministic `front`, `left`, `right` and `back` PNGs in
the existing worker using the dependency-free (beyond Pillow) CPU software renderer. Tests
cover successful labelled metadata, a missing renderer, invalid GLB input, partial per-view
failure and preservation of mock-mode `not_evaluated` behavior.

| Check | Result |
| --- | --- |
| `pytest -q` | PASS: 27 tests |
| `pytest -q tests/test_quality_rendering.py` | PASS: 5 tests |
| `ruff check .` | PASS |
| `ruff format --check .` | PASS: 38 files |
| `mypy app` | PASS: 26 source files |

The pre-existing Starlette/httpx deprecation warning remains; it does not come from the GLB
renderer. No GPU, CUDA, hosted renderer or paid service was installed or added.

## Optional local-model pipeline verification - 2026-11-06

SAM 2 foreground-mask refinement and advisory DINOv2 correspondence are connected to the
aligned-view pipeline through lazy local-only loaders. The test environment used mocked
models and dummy local paths/checkpoints; it downloaded no weights and made no network calls.

| Check | Result |
| --- | --- |
| `pytest -q` | PASS: 33 tests |
| `pytest -q tests/test_quality_analysis.py` | PASS: 10 tests |
| `ruff check .` | PASS |
| `ruff format --check .` | PASS: 38 files |
| `mypy app` | PASS: 26 source files |

Coverage includes default-disabled/lazy behavior, aligned-only invocation, SAM mask-only
refinement, advisory DINOv2 output, local-only loader options, unavailable-dependency fallback
to deterministic metrics and a single CUDA-OOM retry on CPU. The existing Starlette/httpx
deprecation warning remains.

## Docker Compose full-stack validation attempt - 2026-11-06

### Outcome

Container validation is **BLOCKED before Compose execution** on this Windows host. Docker
Desktop and the Docker CLI are not installed, and `wsl.exe --list --verbose` reports that the
Windows Subsystem for Linux is not installed. Therefore this run cannot truthfully confirm a
WSL2 backend, Linux container mode, image builds, container health, PostgreSQL/Redis/RQ/MinIO
connectivity, bucket creation, or live container workflow behavior.

No existing Docker volumes, application databases, buckets, or user data were deleted or
reset. No `docker compose down`, volume-removal, pruning, or destructive database command was
run.

### Host capability evidence

| Command/check | Actual result |
| --- | --- |
| `docker context show` | BLOCKED: PowerShell `CommandNotFoundException`; `docker` is not on PATH. |
| `docker version` | BLOCKED: PowerShell `CommandNotFoundException`. |
| `docker info --format ...` | BLOCKED: PowerShell `CommandNotFoundException`; Linux container mode cannot be inspected. |
| `docker compose version` | BLOCKED: PowerShell `CommandNotFoundException`. |
| `wsl.exe --list --verbose` | BLOCKED: Windows reports that WSL is not installed and suggests `wsl.exe --install`. |
| Docker Desktop executable checks | Not found under `C:\Program Files\Docker\Docker` or `%LOCALAPPDATA%\Docker`. |
| Docker/WSL service query | No matching installed Docker/WSL service was returned. |
| Windows optional-feature query | State could not be read without elevation; command reported that elevation is required. |

Installing/enabling WSL2 and Docker Desktop is a host-level system change that was not
performed implicitly. It may require administrator approval and a Windows restart.

### Compose configuration review

The required Compose command could not run:

```powershell
docker compose config --quiet
```

As a non-equivalent syntax check, the following command parsed `compose.yaml` with the pinned
PyYAML dependency and found all eight service definitions:

```powershell
cd backend
..\.venv\Scripts\python.exe -c "from pathlib import Path; import yaml; data=yaml.safe_load(Path('../compose.yaml').read_text(encoding='utf-8')); print('YAML syntax OK; services=' + ','.join(data['services']))"
```

Result: `YAML syntax OK; services=postgres,redis,minio,storage-init,migrate,api,worker,web`.
This proves YAML syntax only; it is not a substitute for Docker Compose schema,
interpolation, dependency, build, or runtime validation.

One configuration omission was corrected without changing defaults:
`QUALITY_SAM2_CONFIG: ${QUALITY_SAM2_CONFIG:-}` is now passed through the shared worker/API
environment alongside the other optional-quality settings. SAM 2 remains disabled by
default.

The following required commands remain blocked because the `docker` executable is absent:

```powershell
docker compose config --quiet
docker compose up --build -d --wait --wait-timeout 240
docker compose ps
docker compose exec -T api pytest -q
docker compose exec -T api ruff check .
docker compose exec -T api ruff format --check .
docker compose exec -T api mypy app
docker compose exec -T api alembic check
docker compose exec -T api python -m scripts.smoke
docker compose exec -T web npm run lint
docker compose exec -T web npm run typecheck
docker compose exec -T web npm run test -- --run
docker compose exec -T web npm run build
```

### Native validation completed while containers were unavailable

These checks used the repository's existing virtual environment and installed frontend
dependencies. They do not replace the blocked container checks, but they validate the same
application source without changing application behavior.

| Exact command | Result |
| --- | --- |
| `cd backend; ..\.venv\Scripts\python.exe -m pytest -q --tb=short --basetemp D:\PROJECTS\Ayna\.pytest-compose-validation` | PASS: 33 tests; one existing Starlette/httpx deprecation warning. |
| `cd backend; ..\.venv\Scripts\python.exe -m ruff check .` | PASS. |
| `cd backend; ..\.venv\Scripts\python.exe -m ruff format --check .` | PASS: 38 files already formatted. |
| `cd backend; ..\.venv\Scripts\python.exe -m mypy app` | PASS: 26 source files. |
| `cd frontend; npm run lint` | PASS. |
| `cd frontend; npm run typecheck` | PASS. |
| `cd frontend; npm run test -- --run` | PASS: 7 tests across 3 files. |
| `cd frontend; npm run build` | PASS: 2,604 modules transformed; existing approximately 1,013 kB viewer-chunk warning. |

Alembic was checked against a new isolated SQLite database, not the existing application
database:

```powershell
$env:DATABASE_URL = 'sqlite:///D:/PROJECTS/Ayna/backend/.data/alembic-compose-validation-20261106.db'
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m alembic check
..\.venv\Scripts\python.exe -m alembic current
```

Results: `No new upgrade operations detected` and `8a9c2d41f603 (head)`. The agent-created
90,112-byte validation database was then removed after its resolved path was verified inside
`backend/.data`; no pre-existing database was touched.

### Workflow and live smoke evidence

The exact native workflow command was:

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest -q tests\test_workflow.py::test_full_workflow_privacy_idempotency_and_revocation --tb=short --basetemp D:\PROJECTS\Ayna\.pytest-workflow-validation
```

Result: PASS, 2 parameterized cases (two and five photos). The test creates a product, uploads
photos, generates and retrieves the mock GLB, reads the honest `not_evaluated` quality report,
approves the product, confirms public image/model access, rejects it, and confirms both public
assets and the public listing are revoked. It also verifies owner isolation, idempotency, and
append-only approve/reject audits.

The live smoke command was also attempted:

```powershell
cd backend
..\.venv\Scripts\python.exe -m scripts.smoke
```

Result: BLOCKED with `httpx.ConnectError: [WinError 10061]` at `GET /ready` because no API is
listening on `localhost:8000`. This is direct evidence that the live PostgreSQL, Redis/RQ,
MinIO/bucket, migration, API, web, approval, publication, and revocation path was not executed
in containers during this run.

## Pull-request readiness verification - 2026-11-06

The branch was fetched and reviewed against `origin/chore/bootstrap`. The review found no
committed credentials, model weights, build output or large binary artifacts. Optional-model
paths remain local-only and disabled by default. The four shared Dev2 API operations were
confirmed in regenerated OpenAPI: quality detail, review submission, public product list and
public product detail. Generated TypeScript API types match that document.

The only Dev1-owned runtime file changed is
`backend/app/modules/generation/tasks.py`. It invokes the quality service after the mock GLB is
stored, persists private render metadata, keeps mock fidelity `not_evaluated`, and isolates
render/storage failures from generation. This integration point requires Dev1 review before
merge.

| Exact command | Result |
| --- | --- |
| `git fetch --prune origin` | PASS; remote branches refreshed. |
| `python -m pytest -q --tb=short` | PASS: 33 tests; one existing Starlette/httpx deprecation warning. |
| `python -m ruff check .` | PASS. |
| `python -m ruff format --check .` | PASS: 38 files already formatted. |
| `python -m mypy app` | PASS: 26 source files. |
| isolated `alembic upgrade head`, `alembic check`, `alembic current` | PASS: no drift; `8a9c2d41f603 (head)`. |
| `npm run lint` | PASS. |
| `npm run typecheck` | PASS. |
| `npm run test -- --run` | PASS: 9 tests across 4 files. |
| `npm run build` | PASS: 2,070 modules; viewer split into 182.03 kB and 809.04 kB lazy chunks. |

The existing local development database was not upgraded or deleted. Its initial
`alembic check` reported that it was behind head, so migration validation used a fresh temporary SQLite
database which was removed after the successful check.
