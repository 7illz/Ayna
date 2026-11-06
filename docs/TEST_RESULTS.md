# Ayna bootstrap verification — 2026-11-02

Executed in the current Windows workspace with Python 3.12.6, Node 22.21.0 and Docker
29.1.3 using Linux containers (approximately 4 GiB configured memory). These results do
not certify either developer laptop's independent acceptance; use the separate template.
No GPU, CUDA, cloud AI credentials, or paid provider requests were used.

| Check / exact command | Result |
| --- | --- |
| `docker compose config --quiet` | PASS |
| `docker compose up --build -d --wait --wait-timeout 240` | PASS; all six long-running services healthy |
| `docker compose ps` | API/web/worker/PostgreSQL/Redis/MinIO healthy; init/migration exited 0 |
| `docker compose exec -T api pytest -q` | PASS: 16 tests |
| `docker compose exec -T api ruff check .` | PASS |
| `docker compose exec -T api ruff format --check .` | PASS: 31 files |
| `docker compose exec -T api mypy app` | PASS: 22 source files |
| `docker compose exec -T api alembic check` | PASS: no pending schema changes |
| `docker compose exec -T api python -m scripts.smoke` | PASS: 2/5 photos through real RQ/PostgreSQL/MinIO, approval/rejection, owner checks, idempotency, publication/revocation |
| `docker compose exec -T web npm run lint` | PASS |
| `docker compose exec -T web npm run test -- --run` | PASS: 3 tests |
| `docker compose exec -T web npm run build` | PASS: TypeScript + production Vite build |
| Host `npm run types:api` | PASS: frontend types generated from exported FastAPI OpenAPI |
| Host `npm run test:e2e` with `PLAYWRIGHT_BASE_URL=http://localhost:5175` | PASS: 2 Chromium projects, desktop + Pixel 7 viewport |
| `npm audit --omit=dev` | PASS: zero runtime dependency advisories |
| Shared baseline file hash comparison / secret-pattern scan / `git diff --check` | PASS |

Native SQLite/local-files/inline mock mode also passed the complete desktop/mobile browser
workflow. Browser checks cover upload, generated GLB rendering, reset, approval, storefront,
photo gallery, no horizontal overflow, and photograph fallback on an injected model 404.
Backend tests include safe errors, file signature/MIME/byte/pixel rejection, stripped EXIF,
ownership isolation, asset-link tampering, failure handling and deterministic offline GLB.
Every backend test applies and rolls back the explicit Alembic migration.

Local port overrides are in ignored `.env`: API **8001**, web **5175**, matching API/CORS
origins. Another project already owned 8000/5173; its processes were left running. Tracked
defaults remain 8000/5173. Temporary native preview processes are stopped after validation;
the Compose application remains available. Screenshots are in `docs/screenshots/`.

Issues found and fixed: unavailable former MinIO images (now builds pinned upstream source),
dependency peer-version mismatch (compatible pinned TypeScript), non-root container working
directory permissions, signed-URL timestamp comparison in a test, and test concurrency on
limited Docker memory. Browser projects now run sequentially with bounded queue waits.

Non-failing notices: 14 moderate npm advisories remain in development tooling/transitive
dependencies (`npm audit`); no runtime advisories. Do not apply forced major downgrades to
silence the development audit without compatibility review. Starlette emits one test-client
deprecation warning for httpx. Vite reports the lazily imported Three.js viewer chunk at
approximately 1 MB (270 kB gzip). These do not prevent the tested bootstrap workflow.

Production seller identity, paid reconstruction providers, vision evaluation, virtual try-on,
and automatic stale-worker recovery remain later milestones. Mock output is a labeled
dummy; unknown quality metrics are never presented as numerical fidelity scores.
