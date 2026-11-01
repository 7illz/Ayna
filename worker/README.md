# Ayna worker

The shared CPU-safe RQ worker lives in `backend/app/worker.py` and uses the API image.
This directory reserves the optional inference-adapter boundary for later GPU experiments.
No CUDA, local model weights, SAM 2 or DINOv2 are required by the bootstrap.
