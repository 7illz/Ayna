# Codex prompt 3 — integration review after both developer PRs merge

ROLE: Integration engineer for the Ayna prototype. Verify that repository metadata, application title, seller pages, customer viewer, docs and demo screens consistently use **Ayna**; retain the agreed `frontend/` and `backend/` directory names. Both developer feature PRs should have been merged into `main`. Read `docs/PROJECT_BRIEF.md`, `docs/API_CONTRACT.md`, and `README.md`. Pull latest main, create branch `test/end-to-end-integration`, and do not overwrite uncommitted work. Implement fixes and tests, not just suggestions.

Perform and fix an end-to-end scenario in `AI_PROVIDER=mock` WITHOUT CUDA, cloud keys, paid requests or external network dependence:
1. Start all Compose services; ensure DB migrations apply and API/worker/Redis/MinIO/web services are healthy.
2. Create two demo sellers, upload 2 and 5 images to two products and reject invalid/malicious/oversized uploads.
3. Start jobs; verify idempotency, queue processing, pollable terminal state, GLB asset written to object storage, and explicit dummy fixture label.
4. Verify a product is private until authorized seller review approval. Reject and test another product; ensure unauthorized review fails. Verify public catalog only returns approved products.
5. Load seller review and customer 3D viewer on desktop/mobile; check rotation, zoom, reset, screenshot/photo fallback and original image gallery; handle missing and broken model gracefully.
6. Test poor or unmatched reference photos: quality report must say `not_evaluated` / `needs_review` instead of inventing scores.
7. Run backend unit/integration tests, frontend lint/typecheck/build/tests and a browser-oriented smoke test if infrastructure supports it.
8. Ensure README matches exact working commands and Windows Docker/WSL2 setup, optional GPU instructions, `.env.example` and no secret leaks.
9. Add a short `docs/TEST_RESULTS_TEMPLATE.md` for **each laptop's** actual human-executed test result fields: machine, driver/VRAM, commit SHA, commands, PASS/FAIL, screenshots, logs. Do not falsely mark either laptop as tested from your environment.
10. Produce concise failure report, fixes, executed test results, and remaining unsupported cases (e.g. no guaranteed 360-degree accuracy from 2–5 photos). Do not silently change the published API contract.

Commit/push only this integration branch to the correct origin; open PR and request cross-review if `gh` is available. Do not push to `main` or merge without review. After PR is merged, both humans should `git pull --ff-only origin main` and run the complete mock smoke test on both laptops. Use real Meshy/Tripo only in a separate opt-in paid smoke test and never in CI.
