"""Synthesise reproducible test videos with ffmpeg.

Each frame carries a binary *barcode* in a strip across the top that encodes the
frame index exactly: ``nbits`` macroblock-sized blocks, each fully black or
white, read back as the bits of the index. Large, high-contrast, macroblock-
aligned blocks survive H.264 compression intact, so a decoded frame can be
matched back to its *exact* integer index (see :func:`recover_index`). That is
how the random-access benchmark checks *seek correctness*: a backend that
silently returns a neighbouring or keyframe-aligned frame decodes to the wrong
index and is caught with zero ambiguity.

Below the barcode strip, a bright vertical bar sweeps across the frame and mild
per-frame noise is added over a fixed low-frequency texture, giving the encoder
realistic inter-frame motion so decode speed and file sizes are representative
rather than degenerate.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np

from .config import DATA_DIR, VideoSpec

_BAR_WIDTH = 8
_BG_VALUE = 40
_BAR_VALUE = 235

# Barcode geometry. Blocks are macroblock-aligned (16 px) and full black/white
# so they round-trip through H.264 (yuv420p) without bit errors. The strip lives
# in the top-left corner; the moving bar is kept clear of it.
_BLK = 16  # block side in pixels (one bit per block)
_HI, _LO = 255, 0  # bit = 1 / bit = 0 luma value
_CODE_H = _BLK  # height of the barcode strip

_ENCODER = {"h264": "libx264"}


def _nbits(spec: VideoSpec) -> int:
    """Number of barcode bits needed to address every frame of ``spec``."""
    return max(1, int(np.ceil(np.log2(max(2, spec.n_frames)))))


def _bar_step(spec: VideoSpec) -> float:
    """Pixels of horizontal travel per frame for the moving bar (motion only)."""
    usable = spec.width - _BAR_WIDTH
    return usable / max(1, spec.n_frames - 1)


def recover_index(spec: VideoSpec, frame_hwc: np.ndarray) -> int:
    """Recover the exact frame index from a decoded frame's barcode.

    Samples the centre of each barcode block and thresholds it, reconstructing
    the integer index bit by bit (MSB first). Returns the exact integer, so the
    random-access check can require ``recovered == requested`` with no tolerance.
    """
    gray = frame_hwc.astype(np.float32).mean(axis=2)  # H, W
    nbits = _nbits(spec)
    half = _BLK // 2
    value = 0
    for bit in range(nbits):
        x = bit * _BLK + half
        y = half
        # Average a small patch at the block centre for noise robustness.
        patch = gray[max(0, y - 3) : y + 4, max(0, x - 3) : x + 4]
        value = (value << 1) | int(patch.mean() > (_HI + _LO) / 2)
    return value


def _draw_barcode(frame: np.ndarray, spec: VideoSpec, index: int) -> None:
    """Stamp the index as a binary barcode into the top strip of ``frame``."""
    nbits = _nbits(spec)
    for bit in range(nbits):
        msb = (index >> (nbits - 1 - bit)) & 1
        x0 = bit * _BLK
        frame[0:_CODE_H, x0 : x0 + _BLK, :] = _HI if msb else _LO


def _make_frame(spec: VideoSpec, index: int, background: np.ndarray) -> np.ndarray:
    frame = background.copy()
    # Per-frame noise so inter-frame deltas are non-trivial for the encoder.
    rng = np.random.default_rng(1000 + index)
    noise = rng.integers(-6, 7, size=frame.shape, dtype=np.int16)
    frame = np.clip(frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    # Moving bar for realistic motion, kept below the barcode strip.
    x0 = int(round(index * _bar_step(spec)))
    frame[_CODE_H:, x0 : x0 + _BAR_WIDTH, :] = _BAR_VALUE
    # Exact index barcode (drawn last so nothing overwrites it).
    _draw_barcode(frame, spec, index)
    return frame


def _background(spec: VideoSpec) -> np.ndarray:
    rng = np.random.default_rng(abs(hash(spec.name)) % (2**32))
    # Low-frequency texture: upsample a small random field so it compresses into
    # the keyframe but still has spatial detail.
    small = rng.integers(0, 80, size=(spec.height // 16 + 1, spec.width // 16 + 1, 3))
    small = small.astype(np.uint8)
    bg = np.kron(small, np.ones((16, 16, 1), dtype=np.uint8))[
        : spec.height, : spec.width, :
    ]
    return np.clip(bg.astype(np.int16) + _BG_VALUE, 0, 255).astype(np.uint8)


def _ffmpeg_encode(spec: VideoSpec, frames_iter) -> None:
    spec.path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        f"{spec.width}x{spec.height}",
        "-r",
        str(spec.fps),
        "-i",
        "-",
        "-c:v",
        _ENCODER[spec.codec],
        "-g",
        str(spec.gop),
        "-keyint_min",
        str(spec.gop),
        "-crf",
        str(spec.crf),
        "-pix_fmt",
        "yuv420p",
        str(spec.path),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    assert proc.stdin is not None
    for frame in frames_iter:
        proc.stdin.write(frame.tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError(f"ffmpeg failed encoding {spec.name}")


def generate_video(spec: VideoSpec, *, force: bool = False) -> Path:
    """Create ``spec``'s mp4 if missing. Returns its path."""
    if spec.path.exists() and not force:
        return spec.path
    bg = _background(spec)
    _ffmpeg_encode(spec, (_make_frame(spec, i, bg) for i in range(spec.n_frames)))
    return spec.path


def ensure_videos(specs: list[VideoSpec]) -> None:
    for spec in specs:
        generate_video(spec)


def raw_frames(spec: VideoSpec) -> np.ndarray:
    """Return the ground-truth frames (N, H, W, 3) uint8 for write benchmarks."""
    bg = _background(spec)
    return np.stack([_make_frame(spec, i, bg) for i in range(spec.n_frames)])


if __name__ == "__main__":
    from .config import DECODE_VIDEOS

    print(f"Generating into {DATA_DIR}")
    for s in DECODE_VIDEOS:
        p = generate_video(s)
        print(f"  {p.name}: {p.stat().st_size / 1e6:.1f} MB")
