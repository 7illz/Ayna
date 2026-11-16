"""Opt-in RTX integration coverage for sleeve-aware skin recovery."""

import json
import os
import subprocess
from pathlib import Path

import pytest
from PIL import Image


@pytest.mark.skipif(
    os.getenv("AYNA_RUN_FASHN_GPU_TEST") != "1",
    reason="requires authorized private inputs, local weights, and CUDA",
)
def test_skin_recovery_runs_on_cuda_with_valid_output(tmp_path: Path):
    required = {
        name: os.environ.get(name)
        for name in (
            "TRYON_PYTHON",
            "TRYON_WEIGHTS_PATH",
            "AYNA_TRYON_TEST_PERSON",
            "AYNA_TRYON_TEST_GARMENT",
        )
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        pytest.skip(f"missing opt-in environment: {', '.join(missing)}")

    runner = Path(__file__).resolve().parents[2] / "scripts" / "local_fashn_vton.py"
    output = tmp_path / "result.png"
    completed = subprocess.run(
        [
            required["TRYON_PYTHON"],
            str(runner),
            "--weights",
            required["TRYON_WEIGHTS_PATH"],
            "--person",
            required["AYNA_TRYON_TEST_PERSON"],
            "--garment",
            required["AYNA_TRYON_TEST_GARMENT"],
            "--category",
            "tops",
            "--output",
            str(output),
            "--skin-recovery",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=1200,
    )
    runtime = json.loads(completed.stdout.splitlines()[-1])
    assert runtime["device"] == "cuda:0"
    assert runtime["skin_recovery_applied"] is True
    assert runtime["peak_cuda_mib"] < 6144
    with Image.open(output) as image:
        image.verify()
        assert image.format == "PNG"
