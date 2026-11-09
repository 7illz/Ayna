# RTX 4050 and host performance

## Final timeout-repair run - 9 November 2026

The original failed pair completed on final code in 184.237 seconds. Startup/imports completed at
27.445 s and bounded CPU preprocessing completed at 46.914 s; CUDA synthesis completed at
183.915 s. PyTorch reported 3,727.79 MiB peak CUDA allocation. External `nvidia-smi` sampling
observed 98-100% utilization and approximately 5.76-5.78/6.14 GB total VRAM during synthesis.

PyTorch 2.11.0+cu128 uses the RTX 4050 on CUDA 12.8. ONNX Runtime GPU 1.31.1 requires CUDA 13 and
could not load `cublasLt64_13.dll`, so pose inference is deliberately pinned to a bounded CPU
session rather than relying on an implicit provider fallback. No CUDA packages were changed.
Ollama 0.40.15 remains CPU-only, one request/model at a time, and is explicitly unloaded after its
CPU-placement preflight and before FASHN work. Post-run `ollama ps` was empty.

Host measured 8 November 2026:

- AMD Ryzen 5 7535HS: 6 physical / 12 logical cores.
- 16,333,209,600 bytes physical RAM (about 15.2 GiB usable).
- NVIDIA GeForce RTX 4050 Laptop GPU: 6,141 MiB VRAM, driver 616.92.
- User confirmed AC charger and ASUS Turbo mode. Safeguards were not disabled.

Latest real FASHN run: 92.275 seconds, one CUDA job, 3,727.79 MiB peak PyTorch allocation,
approximately 5.84/6.14 GB observed total GPU memory, 100% utilization, about 2.58 GHz and 70 W at
the observed inference point. The earlier accepted execution measured 93.942 seconds and the same
3,727.79 MiB PyTorch peak. GPU work is serialized.

Ollama is intentionally CPU-only: `CUDA_VISIBLE_DEVICES=-1`, `OLLAMA_LLM_LIBRARY=cpu_avx2`, one
parallel request, one loaded model, 4,096-token context. `ollama ps` reported `100% CPU`; NVIDIA
process accounting showed no Ollama allocation. This prevents chatbot traffic from evicting FASHN.

The currently verified profile is the conservative performance profile. A higher-resolution
"quality mode" is not exposed because it has not passed repeated 6 GB runs. CUDA OOM and timeout
are bounded failures; Ayna does not loop indefinitely or report corrupted output as success.
