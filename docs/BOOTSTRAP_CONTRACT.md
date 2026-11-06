# Ayna bootstrap contract details

The copied `API_CONTRACT.md` remains unchanged. Baseline resource fields and enums are
implemented in Pydantic/OpenAPI. These additive details are proposed for bootstrap review.

- IDs are UUIDs. Seller routes require development-only `X-Dev-Seller-Id`.
- Create JSON: `{ "name": "Everyday tote", "category": "bags", "description": "Canvas" }`.
  Returns 201 `ProductOut`; categories: bags/shoes/shirts/pants.
- Upload uses multipart `files` array. Drafts may have one photo; generation requires 2–5.
  Batches validate before writes. No remote URL ingestion. Photo order assigns front first.
- Seller `ProductImageOut` adds a signed `url` for a sanitized derivative. `storage_key`
  stays seller-only; originals are never served by API.
- Generation requires `Idempotency-Key` (1–128 chars) and returns 202 `JobOut` immediately
  in RQ mode. Same product/key returns the same job; a new key during active work gets 409.
  Upload/regeneration immediately unpublishes the product.
- Added `GET /api/v1/products/{id}/generation-jobs` returns newest-first, at most 20 jobs,
  to reconnect after refresh. `JobOut.disclosure` explicitly labels dummy geometry.
- Successful job includes provider `mock`, status `succeeded`, progress 100, signed model
  URL and empty preview URL array. Model URL is null before success. Bootstrap has no
  rendered preview images. Provenance records provider/fixture/license/source count.
- Mock quality is `not_evaluated`, empty metrics, all views uncertain. Before completion,
  quality returns 404. Seller approval records identity/time/notes without changing scores.
- Review JSON: `{ "decision": "approve", "notes": "Checked dummy fixture" }` or reject.
  Requires ownership, current succeeded model and quality report. Returns ProductOut.
- `PublicProduct` contains id/name/category/description, clean image URLs/view tags,
  approved model URL and disclosure. It excludes seller IDs, object keys and private links.
  Images/models check approval per request and return `Cache-Control: no-store`.
- Added `/api/v1/config`: brand/provider/upload limits/development-auth flag, no secrets.
- Both root and `/api/v1` health/readiness routes work. Readiness checks DB/Redis/storage;
  worker heartbeat is a separate Compose health check.
- Errors contain `{ "detail": "...", "request_id": "<uuid>" }` and `X-Request-ID`.
  Validation errors omit raw input. Lists cap at 100; pagination and full CRUD are deferred.
- Settings only accept `AI_PROVIDER=mock`; no hosted adapter can spend credits. Production
  startup rejects development auth, inline queue and default signing key.

State flow: draft → generating → needs_review → approved/rejected. Failure returns product
to draft. Queue outage sets job failed/`QUEUE_UNAVAILABLE`. Atomic worker claims prevent
duplicate processing. Baseline status enums are unchanged; generated schemas are checked
for drift in CI.
