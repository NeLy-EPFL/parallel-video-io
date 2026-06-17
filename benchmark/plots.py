"""Render figures from the consolidated benchmark result CSV.

Reads ``benchmark/results/results.csv`` (or an in-memory DataFrame) and writes
interactive HTML figures to ``benchmark/results/figures``. Figures are embedded
in the docs site via pymdownx.snippets; plotly.js is loaded from CDN.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .config import FIGURES_DIR, RESULTS_DIR

_QUALITY_PARAM_LABEL = {"pvio_gpu": "QP", "opencv": "JPEG Q"}  # all others use CRF

_WORKLOAD_LABEL: dict[str, str] = {
    "enc_sd": "Encoding SD (848×480)",
    "enc_hd": "Encoding HD (1280×720)",
    "sd_h264": "SD (854×480)",
    "hd_h264": "HD (1280×720)",
    "fhd_h264": "Full HD (1920×1080)",
}

_BACKEND_LABEL: dict[str, str] = {
    "pvio_cpu":       "PVIO (CPU)",
    "pvio_gpu":       "PVIO (GPU)",
    "pyav":           "PyAV",
    "pyav_cpu":       "PyAV (CPU)",
    "opencv":         "OpenCV",
    "opencv_cpu":     "OpenCV (CPU)",
    "decord_cpu":     "Decord (CPU)",
    "torchcodec_cpu": "TorchCodec (CPU)",
    "torchcodec_cuda":"TorchCodec (CUDA)",
    "dali_gpu":       "DALI (GPU)",
}

# GPU-based backends (NVENC/NVDEC/DALI). All others are CPU.
_IS_GPU = frozenset({"pvio_gpu", "torchcodec_cuda", "dali_gpu"})

# Two-tone color scheme: PVIO anchor colors, uniform shade for all other CPU/GPU.
_CPU_DARK  = "#0c2e6e"   # PVIO CPU — very dark blue
_CPU_LIGHT = "#90c4e4"   # all other CPU — light blue
_GPU_DARK  = "#7a0042"   # PVIO GPU — dark magenta
_GPU_LIGHT = "#f0a0c4"   # all other GPU — light pink

_BACKEND_COLOR: dict[str, str] = {
    "pvio_cpu":        _CPU_DARK,
    "pvio_gpu":        _GPU_DARK,
    "pyav":            _CPU_LIGHT,
    "pyav_cpu":        _CPU_LIGHT,
    "opencv":          _CPU_LIGHT,
    "opencv_cpu":      _CPU_LIGHT,
    "decord_cpu":      _CPU_LIGHT,
    "torchcodec_cpu":  _CPU_LIGHT,
    "torchcodec_cuda": _GPU_LIGHT,
    "dali_gpu":        _GPU_LIGHT,
}


def _ok(df: pd.DataFrame) -> pd.DataFrame:
    """Rows that produced a finite measurement (drop skipped/errored backends)."""
    return df[df["error"].isna() & df["metric_main"].notna()]


def _pvio_first(backend: str) -> tuple:
    return (0 if backend.startswith("pvio") else 1, backend)


def _decode_order(backend: str) -> tuple:
    """CPU backends first (pvio first within each group), then GPU."""
    return (1 if backend in _IS_GPU else 0, 0 if backend.startswith("pvio") else 1, backend)


def _wl(name: str) -> str:
    return _WORKLOAD_LABEL.get(name, name)


def _be(name: str) -> str:
    return _BACKEND_LABEL.get(name, name)


def _color(backend: str) -> str:
    return _BACKEND_COLOR.get(backend, "#888888")


# Legend group keys and display names for the decode bar chart.
# All non-PVIO CPU backends share one legend entry; same for GPU.
def _legend_group(backend: str) -> str:
    if backend == "pvio_cpu":
        return "pvio_cpu"
    if backend == "pvio_gpu":
        return "pvio_gpu"
    return "other_gpu" if backend in _IS_GPU else "other_cpu"


_LEGEND_GROUP_NAME: dict[str, str] = {
    "pvio_cpu":  "PVIO (CPU)",
    "pvio_gpu":  "PVIO (GPU)",
    "other_cpu": "Other CPU",
    "other_gpu": "Other GPU",
}


def _save(fig: go.Figure, name: str) -> Path:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    path = FIGURES_DIR / name
    fig.write_html(str(path), include_plotlyjs="cdn", full_html=False)
    return path


def plot_encode_quality(df, out: list[Path]):
    sub = _ok(df[df["task"] == "encode_pareto"]).copy()
    if sub.empty:
        return
    # SD first, then HD
    workloads = sorted(sub["workload"].unique(), key=lambda w: (0 if "sd" in w else 1, w))
    backends = sorted(sub["backend"].unique(), key=_pvio_first)
    metrics = [
        ("metric_main",        "Throughput (frames/s)"),
        ("x_compression_ratio","Compression ratio (JPEG folder / video)"),
    ]
    subplot_titles = [
        f"{_wl(wl)} — {label.split('(')[0].strip()}"
        for wl in workloads
        for _, label in metrics
    ]
    fig = make_subplots(rows=len(workloads), cols=2, subplot_titles=subplot_titles)
    for row_idx, workload in enumerate(workloads, start=1):
        wl_display = _wl(workload)
        for backend in backends:
            g = (
                sub[(sub["workload"] == workload) & (sub["backend"] == backend)]
                .sort_values("x_psnr_db")
            )
            if g.empty:
                continue
            param = _QUALITY_PARAM_LABEL.get(backend, "CRF")
            display = _be(backend)
            color = _color(backend)
            cd = list(zip(g["x_quality_param"].astype(int), [wl_display] * len(g)))
            for col_idx, (y_col, y_label) in enumerate(metrics, start=1):
                is_fps = y_col == "metric_main"
                fig.add_trace(
                    go.Scatter(
                        x=g["x_psnr_db"],
                        y=g[y_col],
                        mode="lines+markers",
                        name=display,
                        legendgroup=backend,
                        showlegend=(row_idx == 1 and col_idx == 1),
                        line=dict(color=color),
                        marker=dict(color=color),
                        customdata=cd,
                        hovertemplate=(
                            f"<b>{display}</b><br>"
                            "PSNR: %{x:.1f} dB<br>"
                            f"Param: {param}=%{{customdata[0]}}<br>"
                            + ("Throughput: %{y:.0f} fps" if is_fps else "Compression ratio: %{y:.1f}×")
                            + "<extra></extra>"
                        ),
                    ),
                    row=row_idx, col=col_idx,
                )
            fig.update_xaxes(title_text="PSNR (dB)", row=row_idx, col=1)
            fig.update_xaxes(title_text="PSNR (dB)", row=row_idx, col=2)
            fig.update_yaxes(title_text=metrics[0][1], row=row_idx, col=1)
            fig.update_yaxes(title_text=metrics[1][1], row=row_idx, col=2)
    fig.update_layout(
        title="Encode throughput and compression ratio vs quality",
        hovermode="closest",
        height=700,
        legend_title_text="Backend",
    )
    out.append(_save(fig, "encode_quality.html"))


def plot_decode(df, out: list[Path]):
    TASKS = [
        ("sequential", "Sequential"),
        ("random",     "Precise random-access"),
    ]
    WORKLOADS = ["sd_h264", "hd_h264"]  # SD first (consistent with encode quality plot)

    subplot_titles = [
        f"{_wl(wl)} — {task_label}"
        for wl in WORKLOADS
        for _, task_label in TASKS
    ]
    n_rows, n_cols = len(WORKLOADS), len(TASKS)
    fig = make_subplots(rows=n_rows, cols=n_cols, subplot_titles=subplot_titles)

    # All backends that succeeded in at least one task, CPU-first ordering
    all_backends = sorted(
        {b for tk, _ in TASKS for b in _ok(df[df["task"] == tk])["backend"].unique()},
        key=_decode_order,
    )

    # Each legend group (pvio_cpu, other_cpu, pvio_gpu, other_gpu) appears once.
    shown_lg: set[str] = set()

    for row_idx, workload in enumerate(WORKLOADS, start=1):
        wl_display = _wl(workload)
        for col_idx, (task_key, _) in enumerate(TASKS, start=1):
            sub = _ok(df[df["task"] == task_key])
            wl_data = sub[sub["workload"] == workload]

            # Backends present in this panel, in CPU→GPU order
            panel_backends = [b for b in all_backends if not wl_data[wl_data["backend"] == b].empty]
            n_cpu = sum(1 for b in panel_backends if b not in _IS_GPU)

            for backend in panel_backends:
                g = wl_data[wl_data["backend"] == backend]
                display = _be(backend)
                color = _color(backend)
                lg = _legend_group(backend)
                fig.add_trace(
                    go.Bar(
                        name=_LEGEND_GROUP_NAME[lg],
                        x=[display],
                        y=[float(g["metric_main"].iloc[0])],
                        marker_color=color,
                        legendgroup=lg,
                        showlegend=(lg not in shown_lg),
                        hovertemplate=(
                            f"<b>{display}</b><br>"
                            f"Workload: {wl_display}<br>"
                            "Throughput: %{y:.0f} fps"
                            "<extra></extra>"
                        ),
                    ),
                    row=row_idx, col=col_idx,
                )
                shown_lg.add(lg)

            fig.update_yaxes(
                title_text="Throughput (frames/s)", row=row_idx, col=col_idx
            )

            # Dashed separator between CPU and GPU groups when both are present
            if n_cpu > 0 and n_cpu < len(panel_backends):
                panel_idx = (row_idx - 1) * n_cols + col_idx
                xax = "x" if panel_idx == 1 else f"x{panel_idx}"
                yax = "y" if panel_idx == 1 else f"y{panel_idx}"
                fig.add_shape(
                    type="line",
                    x0=n_cpu - 0.5,
                    x1=n_cpu - 0.5,
                    y0=0,
                    y1=1,
                    xref=xax,
                    yref=f"{yax} domain",
                    line=dict(color="rgba(100,100,100,0.35)", width=1, dash="dot"),
                )

    fig.update_layout(
        title="Decode throughput  (blue = CPU · pink = GPU)",
        hovermode="closest",
        height=700,
        legend_title_text="Backend",
    )
    out.append(_save(fig, "decode_throughput.html"))


def generate(df: pd.DataFrame | None = None) -> list[Path]:
    if df is None:
        csv = RESULTS_DIR / "results.csv"
        if not csv.exists():
            raise FileNotFoundError(f"{csv} not found; run the benchmark first.")
        df = pd.read_csv(csv)
    if "error" not in df:
        df["error"] = pd.NA
    out: list[Path] = []
    plot_encode_quality(df, out)
    plot_decode(df, out)
    return out


if __name__ == "__main__":
    for p in generate():
        print(f"wrote {p}")
