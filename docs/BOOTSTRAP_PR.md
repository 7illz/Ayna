# chore: bootstrap Ayna mock product preview platform

The repository previously contained no application. This change adds the shared Ayna
foundation with a working CPU-only flow from product photos through queued dummy GLB
generation, seller review, and an approved-only storefront.

React/TypeScript/Vite/Tailwind/R3F consume generated FastAPI OpenAPI types. The backend
includes SQLAlchemy/Alembic models, development seller isolation, validated private uploads,
signed asset links, honest unknown quality reports, and RQ/Redis jobs. Compose provides
PostgreSQL and private MinIO built from a pinned upstream source commit. Hosted AI adapters,
production identity and virtual try-on remain separate milestones.

Validation: 16 backend tests, 3 frontend tests, desktop/mobile Chromium workflows including
broken-model fallback, Python/frontend lint and typing, production frontend build, migration
drift checks, and live PostgreSQL/RQ/MinIO smoke for two/five images passed locally. Full
commands and remaining non-failing notices are recorded in `docs/TEST_RESULTS.md`. GitHub
Actions defines the matching automated checks; remote run status must be assessed separately.

Review additive API details in `docs/BOOTSTRAP_CONTRACT.md`. The copied baseline documents
remain byte-for-byte unchanged. Do not merge automatically; bootstrap precedes both feature
branches. Local-only auth and example service credentials require replacement before any
public deployment.
