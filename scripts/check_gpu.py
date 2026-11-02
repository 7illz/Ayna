"""Report optional Ayna vision runtime capability without requiring PyTorch."""

import json
import platform
import subprocess


def main() -> int:
    report: dict[str, object] = {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "nvidia_smi": False,
        "torch_installed": False,
        "cuda_available": False,
        "gpu": None,
        "vram_allocated_mib": None,
    }
    try:
        subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        report["nvidia_smi"] = True
    except (FileNotFoundError, subprocess.SubprocessError):
        pass
    try:
        import torch

        report["torch_installed"] = True
        report["cuda_available"] = torch.cuda.is_available()
        if torch.cuda.is_available():
            report["gpu"] = torch.cuda.get_device_name(0)
            report["vram_allocated_mib"] = round(torch.cuda.memory_allocated(0) / 1024**2, 1)
    except ImportError:
        pass
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
