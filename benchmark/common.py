"""Shared utilities: timing, result records, quality scoring, environment capture."""

from __future__ import annotations

import contextlib
import json
import platform
import subprocess
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

import numpy as np
import torch


@dataclass
class Result:
    """One benchmark measurement row. Serialised to CSV/JSON by the runner."""

    task: str  # "encode", "encode_pareto", "random", "sequential"
    backend: str  # e.g. "pvio_cpu", "torchcodec_cuda", "decord_cpu", "dali_gpu"
    device: str  # "cpu" or "cuda"
    workload: str  # video spec name (e.g. "sd_h264", "enc_hd")
    metric_main: float  # primary number (frames/s)
    metric_unit: str  # "frames/s", "ms/frame", "lines", ...
    extra: dict[str, Any] = field(default_factory=dict)
    error: str | None = None  # set if the backend failed/was skipped

    def flat(self) -> dict[str, Any]:
        d = asdict(self)
        extra = d.pop("extra")
        for k, v in extra.items():
            d[f"x_{k}"] = v
        return d


@contextlib.contextmanager
def timer():
    """Wall-clock timer. Yields a one-element list; result lands in ``out[0]``."""
    out = [0.0]
    start = time.perf_counter()
    try:
        yield out
    finally:
        out[0] = time.perf_counter() - start


def jpeg_baseline_bytes(frames: np.ndarray, quality: int) -> int:
    """Total bytes of *frames* stored individually as JPEGs (compression baseline).

    Used as the denominator-free reference for the compression-ratio metric:
    compression ratio = this / encoded-video-bytes, i.e. how much smaller the
    video is than a folder of per-frame JPEGs at the same quality.
    """
    import cv2

    total = 0
    for frame in frames:
        bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        ok, buf = cv2.imencode(".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, int(quality)])
        if not ok:
            raise RuntimeError("cv2.imencode failed for JPEG baseline")
        total += int(buf.size)
    return total


def decode_back(path: str, indices: list[int]) -> np.ndarray:
    """Decode specific frames back as (k, H, W, 3) uint8 RGB for quality scoring."""
    from torchcodec.decoders import VideoDecoder

    dec = VideoDecoder(path, seek_mode="exact")
    batch = dec.get_frames_at(indices).data  # NCHW uint8
    return batch.permute(0, 2, 3, 1).cpu().numpy()


def quality_psnr_ssim(source: np.ndarray, decoded: np.ndarray) -> tuple[float, float]:
    """Mean PSNR (dB) and SSIM between matched source/decoded frame stacks."""
    from skimage.metrics import peak_signal_noise_ratio, structural_similarity

    # Crop to common dimensions in case a writer changed the frame size.
    h = min(source.shape[1], decoded.shape[1])
    w = min(source.shape[2], decoded.shape[2])
    source, decoded = source[:, :h, :w], decoded[:, :h, :w]
    psnrs, ssims = [], []
    for s, d in zip(source, decoded):
        psnrs.append(peak_signal_noise_ratio(s, d, data_range=255))
        ssims.append(structural_similarity(s, d, channel_axis=2, data_range=255))
    return float(np.mean(psnrs)), float(np.mean(ssims))


def best_of(fn: Callable[[], float], repeats: int) -> float:
    """Run ``fn`` ``repeats`` times, return the best (max) throughput.

    ``fn`` must return a throughput-like number where higher is better.
    """
    best = float("-inf")
    for _ in range(repeats):
        best = max(best, fn())
    return best


def capture_environment() -> dict[str, Any]:
    """Snapshot of hardware/software for reproducibility, stored next to results."""
    env: dict[str, Any] = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "torch": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
    }
    if torch.cuda.is_available():
        env["gpu"] = torch.cuda.get_device_name(0)
        env["cuda"] = torch.version.cuda
    for mod in ("torchcodec", "av", "cv2", "decord"):
        try:
            m = __import__(mod)
            env[mod] = getattr(m, "__version__", "?")
        except Exception:
            env[mod] = None
    try:
        import nvidia.dali as dali

        env["dali"] = dali.__version__
    except Exception:
        env["dali"] = None
    try:
        ff = subprocess.run(
            ["ffmpeg", "-version"], capture_output=True, text=True, check=True
        )
        env["ffmpeg"] = ff.stdout.splitlines()[0]
    except Exception:
        env["ffmpeg"] = None
    env["cpu_count"] = __import__("os").cpu_count()
    return env


def save_environment(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(capture_environment(), indent=2))
