# Codex prompt 1 — Developer 1 (Intel Iris Xe), seller + generation

ROLE: Developer 1 on Intel Iris Xe, full-stack implementation owner for Seller Product Upload + AI Generation. FIRST read `docs/PROJECT_BRIEF.md`, `docs/API_CONTRACT.md`, existing README and OpenAPI schemas. The product and public UI name is **Ayna**; use the shared repo `ayna`. Start only after bootstrap PR is merged. Pull `main`, create `feat/seller-generation`, and do not directly edit Developer 2's quality/storefront modules unless absolutely necessary. You must implement runnable code, tests and documentation, not just a plan.

OWNERSHIP:
- Frontend: `frontend/src/features/seller/` (Ayna-branded seller dashboard, create/edit product, 2–5 image upload with validation and previews, image order/view tags, Start Generation button, async job status/progress, generated GLB preview, error states).
- Backend: `backend/app/modules/catalog/` and `backend/app/modules/generation/`, plus corresponding migrations and tests.
- Queue worker / provider adapters: `mock`, `meshy` (required), `tripo` (optional if API contract verified). Use interface-oriented design with idempotent job processing.
- Storage adapter for local MinIO and R2, preserving private originals and appropriately public approved derivatives; secure temporary URLs.

REQUIREMENTS:
1. Product endpoints per project contract. Allow 2–5 photos per product; do not require 5. Validate product identifiers, seller authorization, file signatures, MIME/size/pixel limits; prevent access to other sellers' files. Add a simple DEV_ONLY mock seller auth or implement minimal real auth clearly documented; do not expose an unauthenticated production seller API.
2. Generation requests start an asynchronous queue job and immediately return a job ID; make polling work. Status transitions must be validated. Prevent accidental duplicate paid jobs via idempotency and explicit per-seller generation limits. Include timeouts, retries only when safe, and sanitized error messages.
3. `AI_PROVIDER=mock` is the DEFAULT and returns an unmistakably dummy GLB generated or stored as a licensed fixture. No tokens or GPU necessary.
4. Implement Meshy multi-image adapter against official current API docs: at most FOUR selected views, original front view FIRST, submit task, poll task, download actual GLB into our storage, record provider task ID and usage metadata. If seller provides five images, choose diverse high-quality four for generation but keep all five for later quality comparisons. Do not assume `model_urls.glb` exists before success. No external provider called during tests. Keep API keys server-side. Treat provider file URLs as untrusted; validate host, size and content when fetching output.
5. Add clear product generation state to seller UI. Handle missing photos, image upload failures, provider errors, 3D generation failures, refresh and retry. An unreviewed GLB must never be publicly listed.
6. Basic frontend tests, backend tests with provider mocks, migration tests, README with local Docker commands. Reuse shared types. Do not change quality threshold or public viewer behavior owned by Dev2.
7. Limit cloud cost: `AI_PROVIDER=meshy` requires deliberate environment opt-in + configured maximum requests; log usage without secrets. Do not spend actual credits in CI.
8. Preserve original input photos and provenance. Never present model-invented details as real scans.

CROSS-TEAM CONTRACT: Extend (do not replace) the bootstrapped `docs/API_CONTRACT.md` with product/job schemas and example JSON; `06_API_CONTRACT_BASELINE.md` supplies the shared baseline. Developer 2 will rely on them. All schema changes need explicit review; no silent changes to status enums.

DELIVERABLES: Working Seller CRUD/upload flow, async mock generation end-to-end, opt-in Meshy adapter, storage, tests, screenshots/demo instructions, PR-ready commits. Run backend tests, frontend lint/build/tests and a local happy-path test. Report exact commands and results. Push only `feat/seller-generation` to the designated origin, open PR if `gh` is configured; do not merge or force push. Never commit `.env` or credentials.
