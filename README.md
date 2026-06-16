# Parallel Video IO

The Parallel Video IO (PVIO) package is motivated by the following problems that I kept having:

1. I could never remember the `ffmpeg` and `ffprob` commands for simple tasks, so I have to Google them every time.
2. Precise random seek in videos (for scientific use) is not so trivial.
3. I just want some simple dataloader that works for ML training _and_ inference.

After finding myself writing the same thing over and over again for different projects, I wrote this package with the following features:

1. Read frames from videos (random access or sequential) using imageio/FFmpeg.
2. Write sequences of NumPy frames to H.264 MP4 files with sensible defaults.
3. PyTorch-compatible `VideoCollectionDataset` and `VideoCollectionDataLoader` that stream frames from many videos in parallel across worker processes.
    - `SimpleVideoCollectionLoader` provides a convenience API that combines dataset and dataloader creation in one call.

**Linux only.** macOS and Windows are not currently supported.

## Installation, code examples, and documentation

See [the documentation site](https://nely-epfl.github.io/parallel-video-io/).


## Development

Clone and install with the dev dependencies:

```bash
git clone git@github.com:sibocw/parallel-video-io.git
cd parallel-video-io
uv sync --extra dev
```

Run the test suite:

```bash
pytest tests
```

Build and preview the documentation site locally:

```bash
uv run mkdocs serve
```
