# Ayna — Developer 1 Codex kit

**Role:** Developer 1 (team lead, Intel Iris Xe).
**Shared GitHub repository:** `OWNER/ayna` (replace OWNER with your GitHub username or organization).
**Branch ownership:** `chore/bootstrap` (first) then `feat/seller-generation`.

## Order of execution

1. Read `00_PROJECT_BRIEF.md` and `06_API_CONTRACT_BASELINE.md`.
2. Create/clone the private `ayna` repository. Run `01_CODEX_BOOTSTRAP.md` in Codex to create the shared foundation. Push `chore/bootstrap`; review/merge it before branching.
3. Pull `main`; give Codex `02_CODEX_DEV1.md` to implement seller upload, asynchronous generation, provider interfaces and storage.
4. Push `feat/seller-generation`, open a PR and coordinate review with Dev2.
5. Follow `04_GITHUB_AND_TESTING.md` on both machines; after both feature PRs merge, run `05_CODEX_INTEGRATION.md` as the final integration prompt.

**Read-first shared documents:** `00_PROJECT_BRIEF.md`, `06_API_CONTRACT_BASELINE.md`. Copy them into `docs/` during bootstrap.

**Note:** This ZIP provides Codex instructions and technical contracts, *not* an implemented website, model weights or a GitHub push. Default mock provider must work with no GPU or paid AI key.
