# RTX 4050 and host performance

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
