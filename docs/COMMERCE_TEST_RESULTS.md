# Commerce verification — 2026-11-02

Local environment: Windows, Python 3.12, Node 22, Chromium desktop and Pixel 7 viewport.
API `http://localhost:8002`, web `http://localhost:5175`. Native mode uses SQLite,
local files and inline mock generation; this is separate from Docker volumes.

| Check | Executed result |
| --- | --- |
| Backend `pytest -q` | 30 passed, including all original 16 tests and 14 commerce tests |
| Ruff lint / format | Passed, 46 Python files formatted |
| Mypy | Passed, 33 application source files |
| Alembic upgrade + drift | Applied additive commerce migration; no new operations detected |
| Frontend ESLint / TypeScript | Passed |
| Frontend Vitest | 3 passed |
| Production Vite build | Passed |
| Generated OpenAPI / TypeScript | Refreshed from executable contracts |
| Live commerce smoke | Passed: photo listing, two concurrent buyers/one unit, exactly one accepted order, COD, owner-only order, cancel/restock |
| Native start/stop helpers | Stopped only recorded Ayna processes, retained data, rebuilt and started both servers; API readiness and web responded |
| Visual inspection | Desktop/mobile homepage inspected; no horizontal overflow |
| Playwright full suite | 6 passed in 51.2 seconds: customer, seller/admin and studio journeys on desktop/mobile |
| Original live mock smoke | Passed with two/five photos, approval/rejection and stored dummy GLB (native inline mode) |
| Compose configuration | `docker compose config --quiet` passed |
| npm production dependency audit | 0 vulnerabilities |

Commerce tests cover cookie security, guest cart merge/privacy, BDT quotes/coupons,
idempotent COD checkout, stock changes, mandatory option selection, ordinary listings
without 3D, search, archival, seller isolation, fulfillment, verified reviews, returns,
COD collection, account suspension, password reset replay, settings and support.
Stripe signed-webhook tests validate signature, amount/currency and replay behavior
without contacting Stripe. Administrator self-protection, unchanged-role session
retention and all-disabled-category behavior are included.

Browser journeys exercise guest search/bag/coupon, registration preserving checkout,
COD, saved address, order tracking, review, wishlist and support; seller listing/photo/
option creation and administrator category/coupon/user/support screens; and the original
studio generation/approval/viewer plus broken-model fallback. The initial seller browser
test exposed delayed sign-out navigation and an ambiguous test selector; both were
corrected before the full passing rerun. Remote CI is recorded separately after completion.

## Host limitation and external configuration

The new local Docker build could not finish because Docker Desktop failed with EOF and
a Windows/WSL distribution startup/file-lock error. No Docker reset or volume deletion
was performed. Native verification continued successfully. Fresh Linux CI is the
separate PostgreSQL/Redis/MinIO verification; the earlier bootstrap CI pass does not
constitute verification of the new commerce changes.

Live Stripe charges/refunds, SMTP delivery, carrier APIs, bank/COD reconciliation and
production HTTPS infrastructure are not configured or tested. The mock GLB remains a
dummy and does not prove reconstruction fidelity or provide clothing/shoe try-on.

Non-failing notices: Starlette's current TestClient emits an httpx deprecation warning;
the lazy-loaded 3D viewer bundle exceeds Vite's 500 kB advisory. The ordinary shop bundle
is separate. These notices did not prevent the tests or production build.
