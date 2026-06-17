"""MkDocs hook: ensure benchmark/results/SUMMARY.md exists before build.

Run the benchmark first (`uv run python -m benchmark.run_all`) to generate
results; figures are embedded via pymdownx.snippets at build time from
benchmark/results/figures/*.html.
"""

from pathlib import Path

_SUMMARY = Path("benchmark/results/SUMMARY.md")
_PLACEHOLDER = "*Run `uv run python -m benchmark.run_all` to generate results.*\n"


def on_pre_build(config):  # noqa: ARG001
    if not _SUMMARY.exists():
        _SUMMARY.parent.mkdir(parents=True, exist_ok=True)
        _SUMMARY.write_text(_PLACEHOLDER)
