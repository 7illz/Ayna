Ayna previously opened into a 3D product studio. It now opens into a general e-commerce
store: products sell with photographs and stock independently of optional 3D approval.
The initial market uses BDT and cash on delivery.

Customers can search/filter, choose options, keep a guest bag, register with cart merge,
use coupons/addresses, place idempotent orders, track delivery, cancel/request returns,
write verified reviews, save wishlists, compare products and contact support. Sellers
manage listings/photos/option inventory and fulfill their own order items. Administrators
manage users, listings, orders/COD collection/returns, categories, coupons, reviews,
support and shipping/tax settings. Cookie identity and private account/order data replace
development-only identity for commerce. Optional Stripe/SMTP adapters are configuration-gated.

Validation: 30 backend tests, 3 frontend tests, lint/typing/formatting, migration drift,
production web build, and live last-unit concurrent checkout/COD/cancellation smoke passed.
Desktop/mobile Chromium journeys cover customers, sellers, administrators and the original
mock GLB approval/viewer workflow. See `docs/COMMERCE_TEST_RESULTS.md` for final results.
Windows start/stop helpers keep the local shop running with a separate SQLite database.

Local Docker Desktop/WSL failed to start during the new build; PostgreSQL/Redis/MinIO
verification therefore relies on the fresh Linux CI run, whose result must be checked
separately. No live payment/email/carrier service is configured. Photorealistic generation
and clothing/shoe try-on remain future work; the mock model is explicitly a dummy.

This PR is based on `chore/bootstrap` because bootstrap PR #1 is still open. Review/merge
the bootstrap first and retarget this PR to `main` afterward. Do not merge automatically.
