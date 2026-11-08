# Virtual try-on diagnosis

## Observed failure

The browser remained on **Uploading** even though the upload, sanitized original, CUDA model, and
worker thread existed. GPU utilization fell idle. This was not a charger, Turbo-mode, CUDA, model
weight, RGB/BGR, or image-dimension problem.

## Root cause

`local_fashn.py` launched the verbose FASHN subprocess with merged stdout/stderr connected to
`subprocess.PIPE`, but the parent did not drain the pipe until `communicate` after inference. Model
and progress output filled the Windows pipe buffer, blocking the child and therefore the inline
HTTP upload request. The eventual timeout correctly failed the job without overwriting its source.

## Repair

- Child output is streamed to a per-run `inference.log`; only the final bounded tail is read for
  diagnostics.
- In native `QUEUE_MODE=inline`, genuine FASHN work starts in a daemon background thread after the
  job is committed. The 202 response is released immediately and the UI polls persisted status.
- Diagnostic test mode stays synchronous and deterministic.
- Result creation remains unique and separate from the immutable sanitized source. Timeout,
  corrupt output, deletion, and late-result suppression fail closed.

## Real execution evidence

Private job `8ade2beb-c5e6-4517-96b9-34241ca822b3`, using a 683×911 person photo and 900×900
garment image, completed in 92.275 seconds on `cuda:0`, with 3,727.79 MiB peak PyTorch allocation.
During synthesis the RTX reached 100% utilization, approximately 2.58 GHz and 70 W; system GPU
memory reached about 5.84/6.14 GB including non-PyTorch allocations. Output was a valid PNG and
the original input remained unchanged.

Human inspection found a plausible white T-shirt transfer with face/background largely preserved,
but visible arm/hand artifacts. This is a technically successful result, not a full visual-quality
acceptance. Shirts/tops are the demonstrated priority. Pants/one-pieces are model capabilities but
not accepted here; shoes and selfie-to-body generation are unsupported.
