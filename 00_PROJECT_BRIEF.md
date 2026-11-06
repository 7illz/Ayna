# Ayna — two-developer implementation brief

**Company/product name:** Ayna (capital A). **GitHub repository:** `ayna`. **Public-facing brand:** Ayna. **This stage:** high-fidelity 3D product preview MVP, not a finished payment/checkout system. Future customer selfie try-on is a separate feature and is **out of scope** for this phase.

## Goal
Build an e-commerce **prototype** that lets sellers upload **2–5 photographs of one real product**, generates a textured 3D model using a hosted provider, runs photo-fidelity checks, requires seller approval, and displays approved results in a customer-facing interactive viewer. The model must not claim hidden sides or invented details are factually verified. Initial product categories: shoes and bags; shirts/pants are treated as experimental and must fall back to original photographs if quality is insufficient.

## Hardware and strategy
- Developer 1 (Intel Iris Xe): build and run the full application in mock/cloud-API mode. No local CUDA dependency.
- Developer 2 (RTX 4050 laptop, typically 6 GB VRAM, 16 GB RAM): same app, plus **optional** CUDA-based preprocessing/analysis experiments. Heavy texturing/3D generation through hosted Meshy/Tripo APIs. Never train a new model during MVP.
- Both machines must be able to run `docker compose up --build` in `AI_PROVIDER=mock`, without credentials or NVIDIA GPU.

## Fixed stack
- Web: React + TypeScript + Vite + Tailwind CSS + React Three Fiber / Three.js. UI header and browser title must say `Ayna`; internal project folder stays `frontend/` to preserve the team contract.
- API: Python 3.11+ + FastAPI + Pydantic + SQLAlchemy + Alembic. API/service display name `Ayna API`; internal project folder stays `backend/`.
- Database: PostgreSQL.
- Background jobs: Celery + Redis or RQ + Redis (select one in scaffold; all devs adhere to it).
- Assets: S3-compatible object-storage adapter: local MinIO for tests, Cloudflare R2 for production.
- Models/services: provider interface (`mock`, `meshy`; `tripo` optional) with real credentials only server-side. Segmentation/quality modules implement optional SAM 2 and DINOv2 where practical, with explicit fallback.
- 3D artifacts: GLB/glTF. No generated asset should be presented as scanned ground truth.

## Repo layout
```
ayna/
  frontend/src/features/seller/
  frontend/src/features/storefront/
  frontend/src/features/review/
  frontend/src/shared/
  backend/app/modules/catalog/
  backend/app/modules/generation/
  backend/app/modules/quality/
  backend/app/modules/public_catalog/
  backend/app/common/
  backend/tests/
  worker/                       # optional inference adapter; CPU-safe default
  infra/
  docs/
  .github/workflows/
  .env.example
  compose.yaml
  README.md
```

## Fixed interfaces (agree before feature work)

The `06_API_CONTRACT_BASELINE.md` in both developer kits is the shared starting contract. Dev1 bootstrap copies it to `docs/API_CONTRACT.md` so Dev2 can work without waiting on Dev1 feature-branch changes. All additions require review and compatibility with these fixed interfaces.
Product: `id`, `seller_id`, `name`, `category`, `description`, `images[]` (2–5 references), `created_at`, `updated_at`.
GenerationJob: `id`, `product_id`, `provider`, `status`, `progress`, `created_at`, `finished_at`, `error_code`, `model_asset_url`, `preview_asset_urls[]`.
QualityReport: `product_id`, `job_id`, `status` (`pending|pass|needs_review|failed|not_evaluated`), `metrics`, `notes`, `uncertain_views[]`, `reviewed_by`, `reviewed_at`.
Product publish status: `draft|generating|needs_review|approved|rejected`.
Allowed job statuses: `queued|processing|succeeded|failed|cancelled`.

API baseline (version prefix `/api/v1`):
- `POST /products`, `GET /products/{id}`, `GET /products` (seller-scoped)
- `POST /products/{id}/images` (image upload, max 5, minimum 2 before generation)
- `POST /products/{id}/generation-jobs`, `GET /generation-jobs/{job_id}`
- `GET /products/{id}/quality`, `POST /products/{id}/review` (approve/reject with notes)
- `GET /store/products`, `GET /store/products/{id}` (approved products only)
- `GET /health`, `GET /ready`

API implementation should use an OpenAPI contract (FastAPI-generated) consumed by frontend types. Avoid undocumented payload changes. Use request IDs and safe error responses.

## Critical product rules
1. Original seller photos are authoritative. AI-generated unseen backs/sides are inferred, never verified.
2. Require seller review and approval before a GLB becomes publicly available.
3. Quality metrics may be **unknown** if cameras/views cannot be aligned. Never fabricate similarity percentages.
4. Mock provider must be free, deterministic, and usable offline. Use a procedurally created *clearly labeled dummy GLB*, not a fake realistic reconstructed product.
5. No public URLs exposing original face/user photos. This phase is **product 3D**, not customer virtual try-on.
6. Input image validation: MIME + file signature, max size and pixels, safe filename handling, EXIF stripping for derivatives, no arbitrary remote URL fetches (SSRF).
7. API keys only in server environment. `.env` is gitignored. Costly provider calls require explicit `AI_PROVIDER=meshy` or `tripo` and a configured spending/request cap.
8. Use licensed images/assets only; generated 3D assets retain provenance and provider metadata.
9. Prioritize real product fidelity; if insufficient, show original photos instead of confident 3D claims.

## Shared milestone sequence
0. Developer 1 scaffolds the repo, composes services, writes API schema skeleton, and opens `chore/bootstrap` PR. Merge **before** both feature branches begin.
1. Developer 1 builds seller+generation vertical slice in `feat/seller-generation`.
2. Developer 2 builds quality+viewer vertical slice in `feat/quality-storefront`.
3. Each opens PR; CI tests; review; merge; both PCs pull main and test in mock mode.
4. Enable Meshy/Tripo integration only after basic mock end-to-end acceptance passes. GPU inference remains optional.

## Definition of done
- A seller can upload exactly 2–5 images, submit generation, see status and previews, review and approve/reject.
- Only approved products appear publicly; customer sees 3D GLB viewer with photo fallback and explicit 'AI-generated 3D preview' disclosure.
- Failing generation, zero/invalid assets, no reference match, and malformed images are handled gracefully.
- `docker compose up --build` + automated test commands work on either Windows machine without CUDA/API keys in mock mode.
- CI passes, no secrets committed, PRs reviewed, README documents setup and limitations.
