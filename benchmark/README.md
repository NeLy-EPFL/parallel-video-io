# PVIO benchmark suite

Benchmarks [parallel-video-io](../README.md) (PVIO) against other video IO
libraries across three tasks — **encoding** (merge frames into a video),
**random access** (precise seek decoding), and **sequential access** — on four
metrics: lines of user code, throughput, compression ratio, and the encode
speed-vs-compression Pareto front. GPU paths (NVENC encode, NVDEC decode,
on-GPU DALI) are used where available.

## Latest results

Pre-run results are in [`results/SUMMARY.md`](results/SUMMARY.md) (pivoted
markdown tables) and [`results/figures/`](results/figures/) (HTML charts).
Re-generate at any time following the steps below.

## Prerequisites

```bash
uv sync --extra benchmark
```

This pulls in PyAV, OpenCV, [eva-decord](https://pypi.org/project/eva-decord/),
NVIDIA DALI, TorchCodec, scikit-image, pandas, and plotly via the `benchmark`
optional-dependency group in [`pyproject.toml`](../pyproject.toml). FFmpeg must
be on `PATH`.

GPU backends (PVIO GPU, TorchCodec CUDA, DALI) require an NVIDIA GPU with CUDA
and the matching NVENC/NVDEC drivers. They are automatically skipped when no GPU
is available.

## Running the benchmark

### Full suite

```bash
uv run python -m benchmark.run_all
```

This runs all three tasks (encode, random access, sequential access), writes
results to `benchmark/results/`, and regenerates the interactive HTML figures.

### Quick smoke run

```bash
uv run python -m benchmark.run_all --quick
```

Reduces frame counts, repeats, and quality-sweep points to finish in a few
minutes. Useful for checking that all backends work before committing to a full
run.

### Partial runs

```bash
uv run python -m benchmark.run_all --only encode
uv run python -m benchmark.run_all --only random sequential
uv run python -m benchmark.run_all --no-figures   # skip figure generation
```

### Regenerate figures only

If `benchmark/results/results.csv` already exists and you only changed
`plots.py`:

```bash
uv run python -m benchmark.plots
```

## Output files

| File | Description |
|------|-------------|
| `results/results.csv` | Every measurement — one row per backend × workload × task |
| `results/SUMMARY.md` | Pivoted markdown tables (embedded in the docs) |
| `results/environment.json` | Hardware and library versions for reproducibility |
| `results/figures/*.html` | Interactive Plotly figures (embedded in the docs) |

Synthetic test videos are generated once into `benchmark/data/` (git-ignored)
and reused across runs.

## Fixing stale test videos

If you see errors like `KeyError: 122` or `Invalid frame index=122` in the
random-access task, your `benchmark/data/` videos were generated with a
different `PVIO_BENCH_NFRAMES` value than the current config. Delete and
regenerate:

```bash
rm -rf benchmark/data/
uv run python -m benchmark.run_all
```

The datagen step runs automatically at the start of any benchmark run and
creates videos matching the current `NFRAMES` setting (default: 300 frames).

## Tuning the workload

All knobs can be overridden via environment variables:

| Variable | Default | Effect |
|----------|---------|--------|
| `PVIO_BENCH_NFRAMES` | `300` | Frames per decode test video |
| `PVIO_BENCH_ENCODE_NFRAMES` | `150` | Frames per encode test clip |
| `PVIO_BENCH_FPS` | `30` | Frame rate of generated videos |
| `PVIO_BENCH_N_REPEATS` | `3` | Timed repetitions (best is reported) |
| `PVIO_BENCH_N_RANDOM_READS` | `100` | Random frames fetched per video |
| `PVIO_BENCH_QUALITY` | `20` | Default CRF/QP for single-point encode |
| `PVIO_BENCH_QUALITY_SWEEP` | `17,19,21,23,25` | CRF/QP values for Pareto sweep |
| `PVIO_BENCH_JPEG_QUALITY` | `95` | JPEG quality for compression-ratio baseline |

## What is measured

| Task | Metric(s) | Backends |
|------|-----------|----------|
| **Encoding** (frames → video) | encode frames/s, compression ratio, PSNR/SSIM, Pareto front | pvio_cpu (libx264), pvio_gpu (NVENC), pyav, opencv (MJPEG) |
| **Random access** (precise seek) | frames/s **and seek correctness** | decord, opencv, pvio cpu/gpu, pyav, torchcodec cpu/cuda |
| **Sequential access** | frames/s | dali, decord, opencv, pvio cpu/gpu, pyav, torchcodec cpu/cuda |

### Metric definitions and fairness

- **Throughput** is frames/s (higher is better) on every task, taking the best
  of `N_REPEATS` timed runs after a warm-up pass.
- **Compression ratio** is `(sum of per-frame JPEG bytes) / (encoded video
  bytes)` — how much smaller the video is than storing each frame as a JPEG
  (quality `JPEG_QUALITY`, default 95). Encoders are compared at the same
  effective quality (CRF for libx264, QP for NVENC, default 20), with PSNR/SSIM
  recorded so size can be read at matched quality.
- **Pareto front** sweeps the quality knob for each tunable encoder, tracing a
  curve in (compression ratio, throughput) space; up and to the right is better.
- **Seek correctness** is verified empirically: each synthetic frame carries a
  bright vertical bar whose position encodes its index. After a random read, we
  recover the index from the decoded pixels and check it matches the request
  (tolerance ≈ 1 frame). A library that silently returns the nearest keyframe
  instead of the requested frame is caught here.

## Backend notes

- **PVIO** appears as **CPU** and **GPU** for both encode (libx264 / NVENC via
  `write_frames_to_video(mode=...)`) and decode (`EncodedVideo(device=...)`).
- **TorchCodec** is benchmarked raw on both **CPU** and **CUDA/NVDEC**. It is
  PVIO's own decode backend, so `pvio_cpu` vs `torchcodec_cpu` (and `pvio_gpu`
  vs `torchcodec_cuda`) shows the wrapper's overhead.
- **DALI** decodes on the GPU; its video reader is a sequential pipeline, so it
  appears in the sequential task only (no precise random seek).
- **Decord**: the PyPI `eva-decord` wheel is CPU-only; random access uses
  `seek_accurate` for frame-accurate seeks.
- **Encoding frame sizes** are multiples of 16: `write_frames_to_video` goes
  through imageio/FFmpeg, which macroblock-pads otherwise, changing the frame
  size and breaking the like-for-like quality comparison.

## Layout

```
benchmark/
  config.py           # all knobs (env-overridable)
  common.py           # timing, mem sampling, Result, JPEG baseline, quality scoring
  datagen.py          # synthesise test videos (index-encoded frames)
  backends/           # encode.py, decode.py — one class per backend
  bench_encode.py     # task 1: encoding (+ Pareto sweep)
  bench_random.py     # task 2: precise random access
  bench_sequential.py # task 3: sequential access
  plots.py            # figures from results.csv
  run_all.py          # orchestrator
```
