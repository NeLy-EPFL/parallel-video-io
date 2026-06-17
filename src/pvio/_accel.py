"""Hardware-acceleration detection and configuration helpers.

This internal module centralises the logic for deciding, at run time, whether
the GPU can be used for decoding (TorchCodec/NVDEC) and encoding (FFmpeg/NVENC).
Detection is best-effort and cached: when no usable GPU path is found, callers
transparently fall back to the CPU defaults so behaviour is identical to a
CPU-only machine.

Nothing here is part of the public API; the public surface auto-selects these
paths so users do not have to think about devices or codecs.
"""

from __future__ import annotations

import functools
import logging
import os
import shutil
import subprocess

logger = logging.getLogger(__name__)


# Encoder names and the default quality knob. A single ``quality`` value drives
# both encoders: it is passed as libx264's CRF and as NVENC's constant QP, which
# share the 0-51 H.264 quantiser scale (lower = higher quality and larger files).
# 20 is conservative vs FFmpeg's default of 23, appropriate for scientific data
# where quality loss should be minimal.
NVENC_CODEC = "h264_nvenc"
LIBX264_CODEC = "libx264"

DEFAULT_QUALITY = 20
DEFAULT_LIBX264_PRESET = "slow"  # better compression efficiency
DEFAULT_NVENC_PRESET = "p7"  # slowest / highest quality NVENC preset


def libx264_params(
    quality: int = DEFAULT_QUALITY, preset: str = DEFAULT_LIBX264_PRESET
) -> list[str]:
    """FFmpeg parameters for CPU H.264 (libx264) at the given CRF and preset."""
    return ["-crf", str(quality), "-preset", preset, "-profile:v", "high"]


def nvenc_params(
    quality: int = DEFAULT_QUALITY, preset: str = DEFAULT_NVENC_PRESET
) -> list[str]:
    """FFmpeg parameters for GPU H.264 (NVENC) at the given constant QP and preset.

    Note: no ``-pix_fmt`` here — imageio adds ``-pix_fmt yuv420p`` itself, and
    duplicating it makes FFmpeg error out.
    """
    return [
        "-preset",
        preset,
        "-tune",
        "hq",  # high-quality tuning
        "-rc",
        "constqp",  # constant quantiser — predictable, like CRF
        "-qp",
        str(quality),
        "-profile:v",
        "high",
    ]


# NVENC refuses to initialise below a hardware-dependent minimum frame size
# (empirically ~145 px wide on consumer NVENC). Frames smaller than this in
# either dimension skip the NVENC attempt and go straight to libx264; the
# runtime fallback in ``write_frames_to_video`` covers any remaining cases.
NVENC_MIN_SIDE = 160


@functools.lru_cache(maxsize=1)
def cuda_available() -> bool:
    """Return True if a CUDA device is visible to PyTorch (cached)."""
    try:
        import torch

        return bool(torch.cuda.is_available())
    except Exception as e:  # pragma: no cover - defensive
        logger.debug("CUDA availability check failed: %s", e)
        return False


@functools.lru_cache(maxsize=None)
def _ffmpeg_has_encoder(exe: str, encoder: str) -> bool:
    """Return True if the FFmpeg binary at *exe* exposes *encoder* (cached)."""
    try:
        out = subprocess.run(
            [exe, "-hide_banner", "-encoders"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except Exception as e:  # pragma: no cover - defensive
        logger.debug("Probing encoders of %s failed: %s", exe, e)
        return False
    return encoder in out.stdout


@functools.lru_cache(maxsize=None)
def nvenc_ffmpeg_exe(encoder: str = NVENC_CODEC) -> str | None:
    """Return the path to an FFmpeg binary that supports *encoder*, or None.

    The FFmpeg shipped with ``imageio-ffmpeg`` is typically built without NVENC,
    so a system FFmpeg is usually required. Candidates are probed in order:

    1. ``$IMAGEIO_FFMPEG_EXE`` (user override),
    2. a system ``ffmpeg`` on ``PATH``,
    3. the bundled ``imageio-ffmpeg`` binary.

    The first one exposing *encoder* wins. Result is cached.
    """
    candidates: list[str] = []

    env_exe = os.environ.get("IMAGEIO_FFMPEG_EXE")
    if env_exe:
        candidates.append(env_exe)

    system_exe = shutil.which("ffmpeg")
    if system_exe:
        candidates.append(system_exe)

    try:
        import imageio_ffmpeg

        candidates.append(imageio_ffmpeg.get_ffmpeg_exe())
    except Exception as e:  # pragma: no cover - defensive
        logger.debug("Could not locate imageio-ffmpeg binary: %s", e)

    seen: set[str] = set()
    for exe in candidates:
        if exe in seen:
            continue
        seen.add(exe)
        if _ffmpeg_has_encoder(exe, encoder):
            logger.debug("Found NVENC-capable FFmpeg for %s: %s", encoder, exe)
            return exe
    return None


def resolve_decode_device(device: str | None) -> str:
    """Resolve a requested decode device to a concrete ``"cpu"``/``"cuda"`` string.

    ``None`` (or ``"auto"``) selects ``"cuda"`` when a CUDA device is available
    and ``"cpu"`` otherwise. Any explicit value is returned unchanged.
    """
    if device is None or device == "auto":
        return "cuda" if cuda_available() else "cpu"
    return device


def can_use_nvenc(height: int, width: int) -> bool:
    """Return True if NVENC encoding should be attempted for this frame size.

    Requires a visible CUDA device, an NVENC-capable FFmpeg, and a frame large
    enough to satisfy NVENC's minimum-dimension constraint.
    """
    if min(height, width) < NVENC_MIN_SIDE:
        return False
    if not cuda_available():
        return False
    return nvenc_ffmpeg_exe() is not None
