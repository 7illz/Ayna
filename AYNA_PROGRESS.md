# Ayna completion progress — 8 November 2026

## Completed and tested

- Fetched all remotes and verified `feat/local-ai-completion` is ahead of, not behind, both
  developer histories. No user work was discarded and no unresolved conflict remains.
- Reproduced the live try-on upload stall. The FASHN subprocess filled an unread Windows pipe;
  inference now logs to a bounded job file and native uploads return immediately while one GPU
  thread processes the persisted job.
- Reprocessed private job `8ade2beb-c5e6-4517-96b9-34241ca822b3` successfully with genuine
  FASHN VTON inference: 92.275 seconds, CUDA device 0, 3,727.79 MiB peak PyTorch allocation.
- Installed official Ollama 0.40.15, pulled `qwen3:0.6b` and
  `qwen3-embedding:0.6b`, verified coherent generation and a 1,024-dimensional embedding.
- Restarted Ollama as localhost-only, one-model/one-request, 4K-context CPU inference. `ollama ps`
  reported `100% CPU`; no Ollama compute process appeared on the NVIDIA GPU.
- Added a LangChain/Ollama product assistant with parameterized live catalog filtering,
  incremental local embeddings, untrusted-description isolation, Bangla numeral/term handling,
  structured product cards, and a deterministic unavailable-model fallback.
- Added the React chat widget and upgraded try-on UI with progress, before/after comparison,
  retry, authenticated download, deletion, and accurate unavailable/failure states.
- Paid Meshy/Tripo selection now fails closed unless a separate explicit override is supplied;
  the provided demo environment keeps that override false.
- Frontend: 15/15 tests passed and production build passed. RAG backend: 3/3 tests passed.

## Remaining validation

- Execute a second new garment/person pair and obtain human acceptance. The current user result
  is technically valid but has visible hand/arm artifacts, so visual-quality acceptance is open.
- Test a physical Intel Iris Xe laptop over a trusted LAN. That device is not accessible here.
- Push the final commit and wait for required GitHub checks/review. Do not merge before review.

Final automated validation is complete: 98 backend tests passed with 1 intentional optional
OpenCV skip; Ruff, format, MyPy, Alembic current/check, OpenAPI generation, frontend lint,
typecheck, 15 component tests, and production build passed. Live English, semantic, and Bangla
requests were repeated; the Bangla no-result is correct because the demo catalog has no black shirt.

## Current blockers

- FASHN's required NVIDIA-derived human parser is noncommercial; this path is demo/research only.
- No verified shoe-on-feet model is available for this 6 GB profile.
- Cross-device validation and a second human-reviewed pair require external input/hardware.

## Files changed in this milestone

Try-on backend/tests and UI; RAG backend/tests/widget; configuration and dependency lock;
Windows Ollama/start/test scripts; required audit, performance, setup, license, and test documents.
