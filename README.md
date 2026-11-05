# Ayna

Ayna's shared product 3D preview foundation: React/TypeScript/Vite/Tailwind + React Three
Fiber; FastAPI/Pydantic/SQLAlchemy/Alembic; PostgreSQL, Redis/RQ and private MinIO.
Create products, upload 2–5 photos, generate a deterministic **dummy GLB**, review it, and
explore approved previews in the storefront. No GPU, model weights or paid API keys.

This prototype does not reconstruct products photorealistically. Hosted AI adapters,
virtual try-on, payments and production identity remain later work. Dev2 adds CPU-safe
aligned-view quality signals plus opt-in local SAM 2/DINOv2 adapter boundaries; no model
weights are included or downloaded automatically.

## Windows setup

Install Git and Docker Desktop with **WSL2 and Linux containers** enabled. Start Docker
Desktop; `docker info` must succeed. Allow several GB for the initial build. MinIO builds
from a pinned upstream commit because the former official community images are unavailable.
The initial build needs internet; installed mock generation never contacts a provider.

```powershell
git clone https://github.com/7illz/Ayna.git
cd Ayna
git switch main
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
docker compose up --build -d --wait --wait-timeout 240
docker compose ps
```

- Web: http://localhost:5173
- API: http://localhost:8000/health and http://localhost:8000/ready
- OpenAPI explorer: http://localhost:8000/docs
- Private MinIO console: http://localhost:9001 (local example credentials in `.env.example`)

Compose starts the six app/infrastructure services plus one-shot migration/bucket setup.
If another application owns the default ports, set `API_PORT`, `WEB_PORT`,
`VITE_API_BASE_URL` and the matching `CORS_ORIGINS` in the ignored `.env`.
Only web/API and the MinIO console bind to loopback. `docker compose down` stops them and
retains data. Migrations apply automatically; no CUDA or NVIDIA runtime is installed.

## Demo

1. In **Product studio**, **Add product**, name/category, and 2–5 JPEG/PNG/WebP photographs.
2. Put a clear front view first. **Generate mock preview** starts an asynchronous RQ job.
3. Rotate/zoom/reset the labeled magenta dummy and compare the original-photo gallery.
4. Review its `not_evaluated` quality disclosure. Approve to publish in **Storefront**, or
   reject to keep it private. Rejection revokes previously public image and model routes.

The development seller UUID is `11111111-1111-4111-8111-111111111111`. Development-only
`X-Dev-Seller-Id` selects ownership; **this is not production authentication**.
`DEV_AUTH_ENABLED=false` disables seller routes. Production startup rejects development
auth/inline queue/default signing key. Implement real identity before public deployment.

Uploads are capped at 10 MiB / 20 million pixels, MIME/signature checked, and assigned
server-generated paths. Originals stay private; galleries serve re-encoded, resized,
metadata-free derivatives. Seller asset links are signed, valid for 15 minutes; reload to
renew. Public routes always check current approval. API keys never enter frontend config.

## Automated checks

```powershell
docker compose exec api pytest -q
docker compose exec api ruff check .
docker compose exec api ruff format --check .
docker compose exec api mypy app
docker compose exec api alembic check
docker compose exec api python -m scripts.smoke
docker compose exec web npm run lint
docker compose exec web npm run typecheck
docker compose exec web npm run test -- --run
docker compose exec web npm run build
```

The live smoke exercises real PostgreSQL/RQ/Redis/MinIO for 2 and 5 photos, idempotency,
quality, ownership, approval and revocation; it leaves rejected fixtures under random
test sellers. Unit tests use isolated SQLite/files, apply and reverse Alembic every test,
and simulate failures. No cloud provider is used. CI runs these checks and the full
Compose/browser workflow. Human laptop results belong in `docs/TEST_RESULTS_TEMPLATE.md`.
Executed bootstrap results and notices are recorded in `docs/TEST_RESULTS.md`. Browser tests
leave labeled demo products under the demo seller.

Browser tests on the host, with Node 22.21+ and the Compose stack running:

```powershell
cd frontend
npm ci
npx playwright install chromium
npm run test:e2e
```

## Native development

Python 3.12 and Node 22.21+ are the tested toolchain. `requirements.lock` and
`package-lock.json` pin dependencies. An explicit development-only inline queue and
SQLite/local storage support standalone mock development when Docker is unavailable:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r backend/requirements.lock
cd backend
$env:DATABASE_URL='sqlite:///./.data/ayna.db'
$env:QUEUE_MODE='inline'
$env:STORAGE_BACKEND='local'
$env:AI_PROVIDER='mock'
..\.venv\Scripts\alembic upgrade head
..\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In another terminal, `cd frontend`, `npm ci`, `npm run dev`. Native RQ with Redis uses
`python -m app.worker`; Windows uses `SimpleWorker`, Docker/Linux uses process-isolated
`Worker`. Compose always uses RQ. Inline mode uses FastAPI background tasks for mock only.

## Contracts and extension points

`docs/PROJECT_BRIEF.md` and `docs/API_CONTRACT.md` are unchanged copies of the kit baseline.
`docs/BOOTSTRAP_CONTRACT.md` records additive behavior. FastAPI generates `docs/openapi.json`;
frontend types derive from it. Regenerate both with every reviewed schema change:

```powershell
cd backend
..\.venv\Scripts\python -m scripts.export_openapi
cd ../frontend
npm run types:api
```

- `backend/app/modules/catalog/`, `generation/` and seller UI: Developer 1 extension points.
- `backend/app/modules/quality/`, `public_catalog/`, review and storefront UI: Dev2 starters.
- `backend/app/common/`: models, schemas, settings, auth, storage and response views.
- `backend/migrations/`: explicit reversible migration; no runtime `create_all`.
- `worker/`: CPU-safe quality boundary with optional isolated SAM 2/DINOv2 loaders.
- `scripts/check_gpu.py`: reports NVIDIA/PyTorch capability without requiring PyTorch.
- `docs/DEV2_QUALITY_STOREFRONT.md`: CPU analysis and opt-in RTX 4050 configuration.
- `backend/fixtures/dummy.glb`: original CC0 fixture; see `docs/ASSET_LICENSES.md`.

`VITE_API_BASE_URL` configures the browser API origin. `CORS_ORIGINS` is an explicit JSON
allowlist. `/api/v1/config` supplies upload limits. The S3 adapter supports private R2 via
server-side endpoint/bucket/region/credentials. `.env` is ignored; example credentials are
public local-development defaults. The original kit README is in `docs/DEVELOPER1_KIT.md`.

## Limits

Mock geometry is unrelated to products. Quality scores are unknown when camera views cannot
be aligned and are never fabricated.
Shirts/pants are experimental and photographs remain authoritative. No guaranteed 360°
fidelity from 2–5 photos. The viewer falls back to photos on unavailable WebGL/broken GLB;
it uses no remote HDR maps/fonts/assets. Full CRUD editing/removal, paid adapters and
automatic stale-worker recovery are future milestones. Work on `chore/bootstrap`; never
push directly to `main` or merge without review.
