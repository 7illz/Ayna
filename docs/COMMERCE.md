# Commerce implementation and contracts

The user's subsequent commerce request extends the original developer kit. Ayna is a
general store; 3D approval is independent of ordinary listing publication. Try-on is
reserved for clothing and shoes and is not supplied by the mock provider.

## Contracts

The authoritative executable contracts are `backend/app/modules/commerce/schemas.py`,
the exported `docs/openapi.json`, and generated `frontend/src/shared/api-schema.d.ts`.
The original developer kit baseline remains documented in `API_CONTRACT.md`.
All business endpoints below use `/api/v1`:

| Area | Routes |
| --- | --- |
| Identity | `/auth/register`, `/auth/login`, `/auth/logout`, `/auth/me`, `/account`, `/account/password`, `/auth/forgot-password`, `/auth/reset-password` |
| Customer | `/account/addresses`, `/wishlist`, `/notifications`, `/support/tickets` |
| Public catalog | `/shop/config`, `/shop/products`, `/shop/products/{id}`, product `/reviews` |
| Shopping | `/cart`, `/cart/items`, `/cart/quote`, `/checkout` |
| Orders | `/orders`, `/orders/{id}`, order `/cancel`, `/return`, `/payment-session` |
| Seller | `/seller/products`, product `/images` and `/variants`, `/seller/orders`, `/seller/order-items/{id}/fulfill` |
| Administration | `/admin/overview`, `/admin/users`, `/admin/products`, `/admin/orders`, `/admin/coupons`, `/admin/categories`, `/admin/settings`, `/admin/reviews`, `/admin/tickets/{id}/reply` |
| Optional hosted payments | `/payments/stripe/webhook` |

See OpenAPI for exact HTTP methods, path parameters and request/response fields.
Refresh both generated artifacts after contract edits:

```powershell
cd backend
..\.venv\Scripts\python.exe -m scripts.export_openapi
cd ..\frontend
npm.cmd run types:api
```

## Data and authorization

The additive Alembic migration introduces users, expiring sessions, reset tokens,
addresses, categories, variants, carts, wishlists, coupons, orders/items/events,
reviews, notifications, support tickets and store settings. Product prices and stock
are additive to the original product model. Money uses integer minor units (BDT poisha).
Order items snapshot names, SKUs, selected options and prices at purchase time.

Passwords use scrypt; only token hashes are stored. HttpOnly, SameSite cookies carry
session tokens; production cookies require HTTPS. Unsafe cookie-authenticated requests
must supply a permitted Origin. Browser requests include credentials. CORS must allow
the exact storefront origin. Production web and API should share the same site.
Login/recovery are throttled. Password resets are single-use and revoke sessions.

Guest bags persist server-side and merge on login/register. Customer order/address data
is owner-scoped. Sellers see only their own items and subtotals in mixed orders, and no
shared order events. Administrator actions require the administrator role. Public API
responses exclude private object keys; photos use sanitized derivatives. Approved 3D
assets retain the separate studio publication checks.

## Checkout and operations

Quotes and checkout independently calculate current prices, coupon eligibility, shipping
and tax. The client cannot choose charged totals. Checkout uses idempotency keys,
customer/product/variant locks and guarded stock decrements; coupon claims serialize.
SQLite native development serializes checkout writes; PostgreSQL uses row locks.
Cancellation releases inventory once. Return approval and refund recording are separate
administrator operations. Seller fulfillment is sequential and shipping requires tracking.
COD collection is recorded by staff after delivery; it is not a bank transfer.

Stripe is optional and hidden until both secrets exist. Hosted checkout uses order
idempotency keys; signed webhooks verify totals/currency and settle once. Failed/expired
sessions restore stock. A payment against an already cancelled order requires manual
reconciliation. Operators must reconcile abandoned unpaid orders and provider refunds;
there is no scheduled reconciliation service. No live merchant account was used in tests.

SMTP is required for production recovery; local mode shows a clearly labeled recovery
link. In-app order/support notifications do not claim to be delivered emails or SMS.
Courier names and tracking numbers are manual, with no external logistics integration.
Only whole-order cancellation/returns are supported; separate partial returns,
seller payouts, accounting exports and a tax jurisdiction engine remain future extensions.

## Local operation

`scripts/start-local.ps1` starts a production Vite preview and an API using mock AI,
inline jobs, SQLite and local files. It builds before serving, checks occupied ports,
records process creation times and keeps logs. `stop-local.ps1` validates workspace and
process identity before terminating those process trees. It preserves databases/assets.
Docker mode uses PostgreSQL/Redis/MinIO; do not assume the databases are shared.
