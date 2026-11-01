# GitHub sync and testing on both Windows laptops

## Phase A — create and bootstrap the shared repository
1. Create **one new private GitHub repository** (required shared name `ayna` (unless both developers explicitly agree to an alternative and update every reference)) or choose an existing, explicitly authorized project. Do not reuse an unrelated repo.
2. Developer 1 clones it; copies `00_PROJECT_BRIEF.md` and `06_API_CONTRACT_BASELINE.md` into `docs/PROJECT_BRIEF.md` and `docs/API_CONTRACT.md`; pastes `01_CODEX_BOOTSTRAP.md` into Codex.
3. Dev1 opens PR from `chore/bootstrap`, waits for CI/review and merges. Ensure Ayna branding, `README.md`, OpenAPI, `compose.yaml`, `.env.example`, and `docs/API_CONTRACT.md` exist.
4. Both developers clone/pull `main`. Now Dev1 creates `feat/seller-generation`, Dev2 creates `feat/quality-storefront`.

PowerShell:
```powershell
git clone https://github.com/OWNER/ayna.git  # replace OWNER with your actual GitHub account or organization
cd ayna
git switch main
git pull --ff-only origin main
git switch -c feat/seller-generation  # Dev1; use feat/quality-storefront on Dev2
```

## Phase B — push and review independently
Never push directly to main. In each branch:
```powershell
git status
git add .
git commit -m "feat: implement assigned vertical slice"
git push -u origin feat/seller-generation  # replace with your branch name
```
Open a pull request via GitHub web UI or, if GitHub CLI is installed:
```powershell
gh pr create --base main --head feat/seller-generation --fill
```
Repeat for teammate's branch. Require successful checks and cross-review before merge. If conflicts arise, rebase/merge latest `main` into the feature branch and resolve carefully. Don't use `--force` on shared branches.

## Phase C — test on Intel Iris Xe and RTX 4050
Requirements: Git, Docker Desktop with WSL2 Linux containers, sufficient disk space. Docker Compose runs PostgreSQL/Redis/MinIO/FastAPI/worker/React with mock provider; no GPU needed.

After each PR merge, **both laptops** run:
```powershell
git switch main
git pull --ff-only origin main
Copy-Item .env.example .env  # only if .env does not already exist
# Edit .env to ensure AI_PROVIDER=mock and required local test config
docker compose up --build -d
docker compose ps
# Open http://localhost:5173 ; http://localhost:8000/docs ; http://localhost:8000/health
```

The bootstrap implementation should ensure these conventional ports and commands work. To run tests (service names `api` and `web` set in compose):
```powershell
docker compose exec api pytest -q
docker compose exec web npm run build
docker compose exec web npm run test -- --run
```

Ensure the home page shows the Ayna brand. If UI is served through a different container, update README and Compose to consistently document the actual URLs. For initial MVP, run `AI_PROVIDER=mock`; verify seller upload -> queue -> dummy GLB -> quality report -> human approval -> published storefront. Real AI output is NOT part of free deterministic tests.

## Phase D — optional RTX 4050 GPU validation
Run on teammate's Windows host (with current NVIDIA driver):
```powershell
nvidia-smi
```
For optional local Python vision environment with a correctly installed CUDA-enabled PyTorch build:
```powershell
python -c "import torch; print('CUDA available:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'none')"
```
Do not assume 6 GB VRAM can load the full 3D shape+texture pipeline. Test SAM 2 Tiny/Small or DINOv2 Small with image resizing and no training; record GPU peak memory, inference latency, and quality. The baseline application must still pass with optional CUDA module disabled.

## Both-laptop manual test matrix
- [ ] Seller creates a shoe product and uploads 2 valid images.
- [ ] Upload rejects 1 image, more than 5 images, and invalid image data.
- [ ] Generation starts, returns immediately, job status updates to succeeded using mock provider.
- [ ] Seller sees *clearly labeled dummy model* and original photo gallery.
- [ ] Product is NOT visible in public storefront before approval.
- [ ] Seller reviews, approves, and product appears publicly with 3D viewer.
- [ ] Rejected model remains private; an unrelated seller cannot approve it.
- [ ] Viewer rotates/zooms, supports reset, handles missing/broken GLB and mobile fallback.
- [ ] Quality report says `not_evaluated` for missing/unmatched reference views; no fabricated scores.
- [ ] App works with no GPU, no paid API key, no background network call to provider.
- [ ] Log and screenshot both machines' results, file issues/PRs for failures.

## Real provider smoke test (after mock path succeeds)
- Enable Meshy or Tripo explicitly in `.env` **on an authorized test account** with a small request/credit cap.
- Use a single real product with front + at least one additional view. For Meshy select up to 4 views and put front first. For Tripo follow its named-view requirements.
- Compare GLB model to source photographs and document inaccuracies before promising accuracy to customers.
- Never commit private images, credentials or paid outputs if license/privacy prohibits doing so.

## Branch and integration rhythm
- Open small PRs by milestone; no 1,000-file code dumps.
- Share `docs/API_CONTRACT.md` updates before frontend/backend changes.
- Prefer feature modules to editing shared root files concurrently.
- Merge bootstrap -> Dev1/Dev2 PRs -> both machines pull `main` -> integration regression test.
- CI must stay fully mock-based, CPU-only and deterministic.

## What cannot be done from this planning kit
It does not write the application itself, push to a particular GitHub repository, or execute tests on either personal laptop. The two Codex agents should implement/push their assigned work, while developers run/verify tests on their own machines.
