# Ayna integration test report — 6 November 2026

Run in `E:\Ayna-integration` on Windows 11, Python 3.12.6, Node 22 and Chromium.
This is one host plus independently executed GitHub Linux CI, not two physical laptop
acceptances. No paid AI task, model weight download, real payment or outbound mail ran.

## Executed baseline and integration checks

Commands use the new worktree's `.venv` unless noted. Initial source review tests used
the existing identically pinned `E:\Ayna\.venv`; a fresh worktree environment was then
installed successfully and `pip check` reported no broken requirements.

| Exact command (working directory) | Result |
| --- | --- |
| `git fetch --all --prune` (original repo) | PASS; three origin branches discovered. |
| `git ls-remote --heads https://github.com/7illz/Ayna.git` | PASS; located the missing D2 feature branch. |
| `git fetch https://github.com/7illz/Ayna.git refs/heads/feat/quality-storefront:refs/remotes/dev2/feat/quality-storefront` | PASS; latest `1190fd6`. |
| `python -m venv .venv` / `.venv\Scripts\python.exe -m pip install -r backend/requirements.lock` (root) | PASS; fresh pinned backend installation. |
| `npm.cmd ci` (frontend) | PASS; 291 packages; 10 moderate development advisories reported. |
| `.venv\Scripts\python.exe -m pip check` (root) | PASS; no broken requirements. |
| `E:\Ayna\.venv\Scripts\python.exe -m pytest -q` (backend, merged D1/D2 baseline) | PASS; 47 tests. |
| Same command after provider/integration fixes (backend) | PASS; 67 tests, 104.86 seconds. |
| `..\.venv\Scripts\python.exe -m pytest -q` (backend, final suite with prior-head and route-uniqueness tests) | PASS; **70 tests**, 135.98 seconds. |
| `..\.venv\Scripts\python.exe -m pytest -q tests/test_migration_paths.py` (backend) | PASS; 2 prior-head upgrade/data-preservation tests. |
| `..\.venv\Scripts\python.exe -m ruff check .` (backend) | PASS. |
| `..\.venv\Scripts\python.exe -m ruff format --check .` (backend) | PASS; 58 files. |
| `E:\Ayna\.venv\Scripts\python.exe -m mypy app` (backend) | PASS; 38 application source files. |
| `..\.venv\Scripts\python.exe -m alembic heads` (backend) | PASS; one head, `e90d9ea58b33`. |
| `..\.venv\Scripts\python.exe -m alembic upgrade head` (backend, via native helper) | PASS; fresh schema at merged head. |
| `..\.venv\Scripts\python.exe -m alembic check` (backend, native SQLite settings) | PASS; no new operations detected. |
| `..\.venv\Scripts\python.exe -m scripts.export_openapi` (backend) | PASS; regenerated contract. |
| `npm.cmd run types:api` (frontend) | PASS; generated shared TypeScript schema. |
| `npm.cmd run lint` / `npm.cmd run typecheck` (frontend) | PASS. |
| `npm.cmd run test -- --run` (frontend) | PASS; 9 tests across 4 files. |
| `npm.cmd run build` (frontend) | PASS; Vite production build, separate lazy Three/viewer chunks. |
| `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start-local.ps1 -ApiPort 8003 -WebPort 5176` (root) | PASS; native API and production preview ready. |
| Native helper stop + `start-local.ps1 -NoSeed -ApiPort 8003 -WebPort 5176` | PASS; owned processes stopped, data preserved and rebuilt. |
| `..\.venv\Scripts\python.exe -m scripts.smoke` (backend, native settings below) | PASS; two/five photos, dummy GLB, quality, approval/rejection, ownership and publication/revocation. Native mode uses inline work despite the historical script's RQ progress label. |
| `..\.venv\Scripts\python.exe -m scripts.commerce_smoke` (backend, native settings below) | PASS; concurrent last-unit checkout, COD, private order, cancel/restock. |
| `npm.cmd run test:e2e` (frontend, native settings below) | PASS; 6 journeys, desktop/Pixel 7, 1.6 minutes. |

Native live-check environment:

```powershell
$env:PYTHONUTF8='1'
$env:SMOKE_API_URL='http://localhost:8003'
$env:STOREFRONT_URL='http://localhost:5176'
$env:PLAYWRIGHT_BASE_URL='http://localhost:5176'
$env:E2E_API_URL='http://localhost:8003'
```

Browser coverage includes guest bag/coupon/register/COD, saved address, delivery tracking,
verified review, wishlist, comparison/removal/recent items, support; seller photos/options
and admin tools; studio photograph direction editing, generation, signed inspection renders,
actual changed canvas pixels after rotate/zoom, reset, approval, public original photos,
mobile overflow and broken-model photo fallback. Screenshots/traces are in the ignored
`frontend/test-results/`; they are not a second physical-PC result.

Hosted-provider tests use `httpx.MockTransport` and controlled fake data only. They cover
single submission, bounded polls, success/failure/incomplete output, task IDs, request caps,
four-of-five/front-first selection, no automatic retries, host restrictions, no redirects,
size limits, GLB validity and worker/private-storage integration. A simulated response does
not establish paid API availability or the appearance/fidelity of a real Meshy result.

## Initial failures found and corrected

- Four merge conflicts: resolved by combining both feature sets, not removing tests.
- Two migration heads: joined by an additive merge revision, tested from both old heads.
- First frontend type/build check failed because its config fixture lacked the new
  `seller_authenticated` field; corrected the typed fixture and reran successfully.
- Initial lint findings in new tests were formatting/import issues; corrected and reran.
- A generation round-trip check found stale generated types after parallel API/type
  generation. Regenerated OpenAPI first and TypeScript second; final stable regeneration
  is checked independently and again in CI.
- Docker engine initially failed because a junction pointed to a nonexistent D: directory.
  Recreated the directory and restarted Desktop; `docker info` returned 29.1.3.
- Private inspection renders had been stored but were not accessible in the seller UI;
  added signed routes and browser coverage. Mock label regression and authenticated studio
  permissions were fixed. Review notes are bounded; full decisions remain in audit rows.

## GPU and other unavailable tests

| Executed command | Actual result |
| --- | --- |
| `E:\Ayna\.venv\Scripts\python.exe scripts/check_gpu.py` | Diagnostic ran: no `nvidia-smi`, no installed torch, no CUDA/GPU reported on this host. Not an RTX acceptance. |
| `E:\Ayna\.venv\Scripts\python.exe scripts/check_vision_runtime.py` | Exit 1 / unavailable: `No module named 'cv2'`. Optional vision packages were not installed into the CPU backend. |

Not executed: real SAM 2 masks, real DINOv2 embeddings, GPU memory/latency/OOM experiments,
live Meshy credits/output fidelity, Tripo, Blender optimization, virtual try-on, real R2,
Stripe settlement/refunds, SMTP delivery and carrier integration. Reasons: no configured
credentials/local weights or applicable GPU here, or feature not implemented. Developer
2's earlier GPU-import/tensor results remain attributed to their report, not relabelled
as this engineer's inference tests. Run the exact separate commands in
`AYNA_BOTH_PC_TESTING.md` on the RTX machine; Intel Iris Xe can run all normal mock tests.

Non-failing notices: existing Starlette/httpx TestClient deprecation, lazy Three chunk
larger than 500 kB, and development dependency advisories. Do not force breaking dependency
downgrades to silence them. Docker startup repair initialized a new disk at the missing
junction target; no earlier disk/volume was deleted or restored.

## Container and GitHub evidence

Container validation uses a distinct Compose project `ayna-integration` and ports 8004/5177,
with BDT/COD/mock/CPU defaults. Remote CI repeats checks on Linux. The final integration PR
contains the immutable tested head SHA, CI links and merge result. Results below are added
only when their commands finish successfully; earlier bootstrap/commerce CI is not reused
as proof that this integration passed.
