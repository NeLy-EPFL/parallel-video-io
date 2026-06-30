"""Repro for the original complaint: reading a single frame was fast but the
pixel values were all 0, 1, or 2.

The video is 16-bit lossless (FFV1, gbrap16le). The old imageio read path
returned 8-bit RGB, keeping only the high byte of each 16-bit sample, so the
small real values (in the hundreds) all collapsed to 0/1/2 and the alpha channel
was dropped. read_frames_from_video now decodes with PyAV at the source's native
depth and channel layout, so the real uint16 values come back intact.
"""

from time import time

import numpy as np

from pvio.io import read_frames_from_video

VIDEO = "20260220_152804_V7_prepup_2-18_11h45_fly_1_V7_prepup_2-18_11h45_20260221_213031_raw_tiff.mkv"

st = time()
frames, fps = read_frames_from_video(VIDEO, frame_indices=[0])
wt = time() - st

frame = frames[0]
unique = np.unique(frame)

print(f"Time taken:   {wt:.3f}s")
print(f"fps:          {fps}")
print(f"dtype:        {frame.dtype}")
print(f"shape:        {frame.shape}  (H, W, C)")
print(f"value range:  min={frame.min()} max={frame.max()}")
print(f"# distinct values: {unique.size}  (first few: {unique[:6]})")

# The original bug: everything collapsed to {0, 1, 2}. Assert we recovered the
# real 16-bit data instead.
assert frame.dtype == np.uint16, f"expected uint16, got {frame.dtype}"
assert frame.max() > 2, (
    f"BUG: all pixel values are <= 2 (max={frame.max()}); 16-bit data was "
    f"truncated to the high byte again."
)
assert unique.size > 3, (
    f"BUG: only {unique.size} distinct values; expected the full uint16 range."
)
print("\nOK: frame decoded at native 16-bit depth with real pixel values.")
