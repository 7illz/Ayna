# Additive integration contract

Baseline UUID fields and product/job/quality status enums are unchanged. Commerce APIs
remain available and normal listing publication remains independent of model approval.
FastAPI exports `docs/openapi.json`; `npm run types:api` generates the shared TS types.

- `GET /api/v1/config` adds `seller_authenticated` (boolean). `dev_auth_enabled` still
  describes the development header shortcut; authenticated sellers/admins may use studio
  creation when it is false. No key, token or provider credential appears in config.
- `PUT /api/v1/products/{id}/images/order` accepts `images: [{id, view_tag}]`. Supply every
  current image exactly once, with the only `front` image first. Other tags are `left`,
  `right`, `side`, `back`, `detail`, `unspecified`. Rejects active generation (409), other
  owners (404), missing/duplicate references or invalid directions (422). It returns
  `ProductOut` and revokes 3D publication by setting `draft`.
- Generation POST remains 202 + `JobOut`. `provider` is `mock` or explicitly configured
  `meshy`; unsupported providers fail configuration. The existing idempotency key returns
  its original job without consuming quota. New requests can return 429 when the seller
  or hosted rolling-24-hour allowance is exhausted. Meshy requires RQ; default inline
  development remains mock. Timeout/failure codes are controlled strings, not raw responses.
- `JobOut.preview_asset_urls` now contains available private inspection PNG URLs in
  front/left/right/back order. URLs are expiring signed bearer links, not storage keys.
  `/assets/render-{view}/{job_id}` checks signature, owner and successful job state.
  Ordinary public product responses do not expose private inspection object keys.
- Disclosures are provider-specific. Mock is explicitly dummy; hosted geometry is an
  estimated preview with unverified fidelity. A successful download is not a quality pass.
- Public list/detail/images/model require current approval, current successful GLB and
  commerce archival/listing/seller guards. Rejected, changed-reference or archived models
  are immediately unavailable publicly. Normal photo-only commerce products remain listed.
- Each seller decision appends a `ReviewAudit`. `QualityReport.notes` retains analysis
  plus the latest bounded note, while audit records preserve all complete decision notes.
- The `e90d9ea58b33` merge revision joins `1d34b4f763de` (commerce) and `8a9c2d41f603`
  (review audit). Neither developer's historical migration is rewritten. Upgrade tests
  start from each prior head with a real product row and verify preservation.

All hosted-provider tests use simulated HTTP. SAM 2/DINOv2 quality flags remain false by
default; configured loaders accept local weights only. Camera labels alone do not prove
alignment, so hosted generation does not automatically score seller-reference fidelity.
