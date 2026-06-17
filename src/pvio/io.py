import numpy as np
import json
import logging
import os
import tempfile
import contextlib
import imageio.v2 as imageio
from pathlib import Path

from . import _accel


logger = logging.getLogger(__name__)


@contextlib.contextmanager
def _imageio_ffmpeg_exe(exe: str | None):
    """Temporarily point imageio-ffmpeg at *exe* via ``IMAGEIO_FFMPEG_EXE``.

    Used to route NVENC encodes through a system FFmpeg, since the binary
    bundled with imageio-ffmpeg is usually built without NVENC. A no-op when
    *exe* is None. Restores the previous environment on exit.
    """
    if exe is None:
        yield
        return
    sentinel = object()
    prev = os.environ.get("IMAGEIO_FFMPEG_EXE", sentinel)
    os.environ["IMAGEIO_FFMPEG_EXE"] = exe
    try:
        yield
    finally:
        if prev is sentinel:
            os.environ.pop("IMAGEIO_FFMPEG_EXE", None)
        else:
            os.environ["IMAGEIO_FFMPEG_EXE"] = prev


def read_frames_from_video(
    video_path: Path | str, frame_indices: list[int] | None = None
) -> tuple[list[np.ndarray], float | None]:
    """Read specific frames from a video file.

    Args:
        video_path: Path to the video file.
        frame_indices: Frame indices to read. If ``None``, reads all frames.

    Returns:
        A 2-tuple ``(frames, fps)``. *frames* is a list of uint8 numpy arrays
        in ``(H, W, C)`` format. *fps* is the FPS reported by the container,
        or ``None`` if unavailable.
    """
    frames = []
    with imageio.get_reader(video_path) as reader:
        if frame_indices is None:
            frame_indices = list(range(reader.count_frames()))
        for frame_id in frame_indices:
            frames.append(reader.get_data(frame_id))
        fps = reader.get_meta_data().get("fps", None)
    return frames, fps


def write_frames_to_video(
    video_path: Path | str,
    frames: list[np.ndarray],
    fps: float,
    *,
    mode: str = "auto",
    quality: int = _accel.DEFAULT_QUALITY,
    preset: str | None = None,
    extra_ffmpeg_params: list[str] | None = None,
    log_interval: int | None = None,
) -> None:
    """Write a sequence of frames to an H.264 MP4 file.

    The encoder is chosen by *mode*: ``"gpu"`` encodes on the GPU (H.264 NVENC),
    ``"cpu"`` on the CPU (libx264), and ``"auto"`` (default) uses the GPU when a
    CUDA device and NVENC-capable FFmpeg are available, else the CPU. Either way
    the encode always falls back to libx264 if NVENC fails (e.g. frames below
    NVENC's minimum size), so output is always produced.

    Quality is controlled by the single *quality* knob, applied as libx264's CRF
    on the CPU path and as NVENC's constant QP on the GPU path — both on the same
    0-51 H.264 quantiser scale where lower means higher quality and larger files.
    The default of 20 is visually lossless and conservative, suitable for
    scientific data.

    Args:
        video_path: Path for the output video file.
        frames: Frames as uint8 numpy arrays in ``(H, W, C)`` format. All
            frames must share the same spatial dimensions.
        fps: Frames per second of the output video.
        mode: Encoder selection — ``"auto"`` (default), ``"gpu"``, or ``"cpu"``.
            ``"gpu"`` forces the NVENC path (falling back to libx264 if NVENC is
            unavailable for the input); ``"cpu"`` forces libx264; ``"auto"``
            picks the GPU when available.
        quality: Encode quality on the 0-51 H.264 quantiser scale (lower = higher
            quality, larger files). Applied as libx264's CRF or NVENC's QP
            depending on the chosen encoder, so it behaves consistently across
            the CPU and GPU paths.
        preset: Encoder preset. ``None`` uses a sensible per-encoder default
            (``"slow"`` for libx264, ``"p7"`` for NVENC). If given, it is passed
            to whichever encoder runs — use encoder-appropriate values
            (libx264: ``ultrafast``…``placebo``; NVENC: ``p1``…``p7``).
        extra_ffmpeg_params: Optional raw FFmpeg parameters appended after the
            quality/preset flags, as an escape hatch for advanced options.
        log_interval: If set, log progress every *log_interval* frames at
            ``INFO`` level.

    Raises:
        ValueError: If *frames* is empty, contains frames with mismatched
            dimensions, or *mode* is not one of ``"auto"``/``"gpu"``/``"cpu"``.
    """
    if mode not in ("auto", "gpu", "cpu"):
        raise ValueError(f"mode must be 'auto', 'gpu', or 'cpu', got {mode!r}.")

    # Check frame size consistency
    if len(frames) == 0:
        raise ValueError("No frames provided to write_frames_to_video")
    frame_size = frames[0].shape[:2]
    for frame in frames:
        if frame.shape[:2] != frame_size:
            raise ValueError(
                "All frames must have the same dimensions. The 0th frame has size "
                f"{frame_size}, but at least one frame has size {frame.shape[:2]}."
            )
    height, width = frame_size[0], frame_size[1]
    extra = list(extra_ffmpeg_params or [])

    # Decide whether to attempt NVENC. "auto" detects a usable GPU; "gpu" forces
    # it when the input/host allow; "cpu" stays on libx264.
    want_gpu = _accel.cuda_available() if mode == "auto" else (mode == "gpu")
    nvenc_usable = want_gpu and _accel.can_use_nvenc(height, width)
    if mode == "gpu" and not nvenc_usable:
        logger.warning(
            "mode='gpu' requested, but NVENC is unavailable for this input "
            "(no CUDA device / NVENC-capable FFmpeg, or frame too small); "
            "encoding with libx264 on the CPU instead."
        )

    # Build the ordered list of (codec, params, ffmpeg_exe) encode attempts. NVENC
    # is tried first when usable, always with a libx264 fallback so output is
    # produced even if the GPU encode fails. The libx264 fallback uses its own
    # default preset (a user-supplied preset is assumed NVENC-specific in that
    # case), but applies the requested quality.
    attempts: list[tuple[str, list[str], str | None]] = []
    if nvenc_usable:
        nvenc_preset = preset or _accel.DEFAULT_NVENC_PRESET
        attempts.append(
            (
                _accel.NVENC_CODEC,
                _accel.nvenc_params(quality, nvenc_preset) + extra,
                _accel.nvenc_ffmpeg_exe(),
            )
        )
        libx264_preset = _accel.DEFAULT_LIBX264_PRESET
    else:
        libx264_preset = preset or _accel.DEFAULT_LIBX264_PRESET
    attempts.append(
        (
            _accel.LIBX264_CODEC,
            _accel.libx264_params(quality, libx264_preset) + extra,
            None,
        )
    )

    last_error: Exception | None = None
    for attempt_idx, (attempt_codec, attempt_params, ffmpeg_exe) in enumerate(attempts):
        is_last = attempt_idx == len(attempts) - 1
        try:
            with _imageio_ffmpeg_exe(ffmpeg_exe):
                _encode_frames(
                    video_path, frames, fps, attempt_codec, attempt_params, log_interval
                )
            return
        except Exception as e:
            last_error = e
            if is_last:
                raise
            logger.warning(
                "Encoding with codec %r failed (%s); falling back to %r.",
                attempt_codec,
                e,
                attempts[attempt_idx + 1][0],
            )
    # Unreachable: the last attempt either returns or re-raises.
    if last_error is not None:  # pragma: no cover - defensive
        raise last_error


def _encode_frames(
    video_path: Path | str,
    frames: list[np.ndarray],
    fps: float,
    codec: str,
    ffmpeg_params: list[str],
    log_interval: int | None,
) -> None:
    """Encode *frames* to *video_path* with imageio's FFmpeg backend."""
    with imageio.get_writer(
        str(video_path),
        "ffmpeg",
        fps=fps,
        codec=codec,
        quality=None,  # Use CRF/QP (in ffmpeg_params) instead of quality
        ffmpeg_params=ffmpeg_params,
    ) as video_writer:
        for i, frame in enumerate(frames):
            video_writer.append_data(frame)

            if log_interval is not None and (i + 1) % log_interval == 0:
                logger.info(f"Written frame {i + 1}/{len(frames)}")


def check_num_frames(video_path: Path | str) -> int:
    """Return the number of frames in a video file.

    Args:
        video_path: Path to the video file.

    Returns:
        Total frame count.

    Raises:
        RuntimeError: If the file cannot be opened.
    """
    try:
        with imageio.get_reader(video_path) as reader:
            num_frames = reader.count_frames()
    except Exception as e:
        raise RuntimeError(f"Failed to open video file: {video_path}") from e
    return num_frames


def get_video_metadata(
    video_path: Path | str,
    cache_metadata: bool = True,
    use_cached_metadata: bool = True,
    metadata_suffix: str = ".metadata.json",
) -> dict[str, int | tuple[int, int] | float | None]:
    """Return frame count, frame size, and FPS for a video file.

    Results are cached to a sidecar JSON file alongside the video to avoid
    re-reading on subsequent calls.

    Args:
        video_path: Path to the video file.
        cache_metadata: Write metadata to a cache file after reading.
        use_cached_metadata: Return cached metadata if the sidecar file
            exists. Set to ``False`` to force a fresh read.
        metadata_suffix: Suffix appended to the video filename to form the
            cache path. Default: ``".metadata.json"``.

    Returns:
        Dictionary with keys ``"n_frames"`` (int total frame count),
        ``"frame_size"`` (tuple ``(height, width)``), and ``"fps"``
        (float or ``None`` if unavailable).
    """
    video_path = Path(video_path)
    cache_path = video_path.parent / (video_path.name + metadata_suffix)
    metadata = {}
    if use_cached_metadata and cache_path.is_file():
        try:
            with open(cache_path, "r") as f:
                metadata = json.load(f)
            n_frames = metadata["n_frames"]
            frame_size = tuple(metadata["frame_size"])
            fps = metadata["fps"]
        except Exception as e:
            logger.critical(f"Corrupted metadata cache file {cache_path}: {e}")
            raise
    else:
        n_frames = check_num_frames(video_path)
        sample_frames, fps = read_frames_from_video(video_path, frame_indices=[0])
        frame_size = sample_frames[0].shape[:2]

        if cache_metadata:
            metadata = {
                "n_frames": n_frames,
                "frame_size": list(frame_size),
                "fps": fps,
            }
            with tempfile.NamedTemporaryFile(
                mode="w", dir=cache_path.parent, suffix=".tmp", delete=False
            ) as tmp_f:
                tmp_path = tmp_f.name
                json.dump(metadata, tmp_f, indent=2)
            os.replace(tmp_path, cache_path)

    return {"n_frames": n_frames, "frame_size": frame_size, "fps": fps}
