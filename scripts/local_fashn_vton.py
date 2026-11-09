"""Small offline CLI boundary for the optional FASHN VTON environment."""

import argparse
import json
import os
import time
from pathlib import Path

PROCESS_STARTED = time.perf_counter()

EVENT_PREFIX = "AYNA_STAGE "


def emit(stage: str, event: str, started: float, **metadata) -> None:
    payload = {
        "stage": stage,
        "event": event,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }
    if metadata:
        payload["metadata"] = metadata
    print(EVENT_PREFIX + json.dumps(payload, sort_keys=True), flush=True)


class CallStageProxy:
    def __init__(self, target, stage: str, started: float, expected_calls: int = 1):
        self.target = target
        self.stage = stage
        self.started = started
        self.expected_calls = expected_calls
        self.calls = 0

    def __getattr__(self, name):
        return getattr(self.target, name)

    def __call__(self, *args, **kwargs):
        if self.calls == 0:
            emit(self.stage, "started", self.started)
        result = self.target(*args, **kwargs)
        self.calls += 1
        if self.calls >= self.expected_calls:
            emit(self.stage, "completed", self.started)
        return result


class PredictStageProxy:
    def __init__(self, target, started: float):
        self.target = target
        self.started = started
        self.calls = 0

    def __getattr__(self, name):
        return getattr(self.target, name)

    def predict(self, *args, **kwargs):
        if self.calls == 0:
            emit("human_parsing", "started", self.started)
        result = self.target.predict(*args, **kwargs)
        self.calls += 1
        if self.calls >= 2:
            emit("human_parsing", "completed", self.started)
        return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--weights", required=True)
    parser.add_argument("--person", required=True)
    parser.add_argument("--garment", required=True)
    parser.add_argument("--category", choices=["tops", "bottoms", "one-pieces"], required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    import onnxruntime as ort
    import torch
    from fashn_human_parser import FashnHumanParser as UpstreamHumanParser
    from PIL import Image

    started = PROCESS_STARTED
    emit(
        "process_startup",
        "completed",
        started,
        torch_version=torch.__version__,
        torch_cuda=torch.version.cuda,
        cuda_available=torch.cuda.is_available(),
        cuda_device=torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        ort_version=ort.__version__,
        ort_available_providers=ort.get_available_providers(),
    )

    # ONNX Runtime 1.31 requires CUDA 13/cuDNN 9, while this verified PyTorch runtime is
    # CUDA 12.8. Use an explicit, bounded CPU session for DWPose instead of triggering a
    # noisy failed CUDA provider load and an implicit fallback. Main synthesis remains CUDA.
    session_options = ort.SessionOptions()
    session_options.intra_op_num_threads = max(1, min(4, (os.cpu_count() or 2) // 2))
    session_options.inter_op_num_threads = 1
    session_options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    original_session = ort.InferenceSession

    def bounded_session(*session_args, **session_kwargs):
        session_kwargs["sess_options"] = session_options
        session_kwargs["providers"] = ["CPUExecutionProvider"]
        session_kwargs.pop("provider_options", None)
        return original_session(*session_args, **session_kwargs)

    ort.InferenceSession = bounded_session

    from fashn_vton import TryOnPipeline as UpstreamTryOnPipeline
    from fashn_vton import pipeline as pipeline_module
    from fashn_vton.dwpose import DWposeDetector

    parser_path = Path(args.weights) / "parser"
    if not parser_path.is_dir():
        raise FileNotFoundError("Pinned local human parser weights are missing")

    class LocalHumanParser(UpstreamHumanParser):
        def __init__(self, device=None):
            super().__init__(model_id=str(parser_path), device=device)

    pipeline_module.FashnHumanParser = LocalHumanParser

    preprocessing_calls = 0
    original_clothing = pipeline_module.create_clothing_agnostic_image
    original_garment = pipeline_module.create_garment_image

    def staged_clothing(*call_args, **call_kwargs):
        nonlocal preprocessing_calls
        if preprocessing_calls == 0:
            emit("garment_preprocessing", "started", started)
        result = original_clothing(*call_args, **call_kwargs)
        preprocessing_calls += 1
        return result

    def staged_garment(*call_args, **call_kwargs):
        nonlocal preprocessing_calls
        if preprocessing_calls == 0:
            emit("garment_preprocessing", "started", started)
        result = original_garment(*call_args, **call_kwargs)
        preprocessing_calls += 1
        emit("garment_preprocessing", "completed", started)
        return result

    pipeline_module.create_clothing_agnostic_image = staged_clothing
    pipeline_module.create_garment_image = staged_garment

    class StagedTryOnPipeline(UpstreamTryOnPipeline):
        def _setup_pose_model(self):
            dwpose_dir = str(Path(self.weights_dir) / "dwpose")
            self.pose_model = DWposeDetector(checkpoints_dir=dwpose_dir, device="cpu")

        def _sample(self, **kwargs):
            emit("cuda_synthesis", "started", started)
            result = super()._sample(**kwargs)
            emit("cuda_synthesis", "completed", started)
            return result

    emit("model_loading", "started", started)
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
    torch.set_num_threads(max(1, min(4, (os.cpu_count() or 2) // 2)))
    torch.set_num_interop_threads(1)
    pipeline = StagedTryOnPipeline(weights_dir=args.weights)
    pipeline.pose_model = CallStageProxy(pipeline.pose_model, "pose_detection", started, 2)
    pipeline.hp_model = PredictStageProxy(pipeline.hp_model, started)
    emit(
        "model_loading",
        "completed",
        started,
        synthesis_device=str(pipeline.device),
        synthesis_dtype=str(pipeline.inference_dtype),
        pose_providers=["CPUExecutionProvider"],
        pose_fallback_reason="ONNX Runtime 1.31 requires CUDA 13; PyTorch runtime uses CUDA 12.8",
        cpu_threads=torch.get_num_threads(),
    )
    result = pipeline(
        person_image=Image.open(args.person).convert("RGB"),
        garment_image=Image.open(args.garment).convert("RGB"),
        category=args.category,
    )
    emit("image_encoding", "started", started)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    result.images[0].save(output, "PNG", optimize=True)
    emit("image_encoding", "completed", started)
    print(
        json.dumps(
            {
                "elapsed_seconds": round(time.perf_counter() - started, 3),
                "device": "cuda:0" if torch.cuda.is_available() else "cpu",
                "peak_cuda_mib": (
                    round(torch.cuda.max_memory_allocated() / 1024**2, 2)
                    if torch.cuda.is_available()
                    else None
                ),
            }
        )
    )


if __name__ == "__main__":
    main()
