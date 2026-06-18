# Benchmark summary

## Encoding at matched PSNR (frames/s and compression at equal image quality, interpolated from the sweep; x_psnr_matched=False means the encoder's sweep did not reach the target and the nearest point is shown)

| workload | backend | x_target_psnr | x_psnr_db | x_psnr_matched | metric_main | x_compression_ratio | x_file_size_mb |
| --- | --- | --- | --- | --- | --- | --- | --- |
| enc_hd | opencv | 34.64 | 36.1 | False | 235.5 | 7.4 | 5.0 |
| enc_hd | pvio_cpu | 34.64 | 34.64 | True | 93.0 | 16.8 | 2.19 |
| enc_hd | pvio_gpu | 34.64 | 34.64 | True | 205.2 | 43.2 | 0.85 |
| enc_hd | pyav | 34.64 | 34.64 | True | 42.4 | 4.4 | 8.37 |
| enc_sd | opencv | 34.6 | 36.08 | False | 527.9 | 7.2 | 2.29 |
| enc_sd | pvio_cpu | 34.6 | 34.59 | True | 156.8 | 14.2 | 1.15 |
| enc_sd | pvio_gpu | 34.6 | 34.59 | True | 303.6 | 42.6 | 0.38 |
| enc_sd | pyav | 34.6 | 34.59 | True | 75.6 | 4.4 | 3.72 |

## Encoding Pareto sweep (throughput vs compression per quality level)

| workload | backend | x_quality_param | metric_main | x_compression_ratio | x_psnr_db |
| --- | --- | --- | --- | --- | --- |
| enc_hd | opencv | 51.0 | 241.593 | 7.4 | 36.1 |
| enc_hd | opencv | 55.0 | 240.101 | 7.4 | 36.1 |
| enc_hd | opencv | 59.0 | 238.131 | 7.4 | 36.1 |
| enc_hd | opencv | 63.0 | 240.417 | 7.4 | 36.1 |
| enc_hd | opencv | 67.0 | 235.465 | 7.4 | 36.1 |
| enc_hd | pvio_cpu | 17.0 | 38.629 | 2.1 | 35.64 |
| enc_hd | pvio_cpu | 19.0 | 50.955 | 4.4 | 35.18 |
| enc_hd | pvio_cpu | 21.0 | 72.985 | 9.6 | 34.94 |
| enc_hd | pvio_cpu | 23.0 | 98.946 | 19.4 | 34.57 |
| enc_hd | pvio_cpu | 25.0 | 133.618 | 47.1 | 34.17 |
| enc_hd | pvio_gpu | 17.0 | 204.122 | 6.1 | 35.36 |
| enc_hd | pvio_gpu | 19.0 | 208.362 | 14.3 | 35.18 |
| enc_hd | pvio_gpu | 21.0 | 204.46 | 38.8 | 34.77 |
| enc_hd | pvio_gpu | 23.0 | 206.788 | 54.4 | 34.38 |
| enc_hd | pvio_gpu | 25.0 | 200.677 | 80.6 | 34.21 |
| enc_hd | pyav | 17.0 | 31.099 | 2.1 | 35.08 |
| enc_hd | pyav | 19.0 | 42.111 | 4.3 | 34.65 |
| enc_hd | pyav | 21.0 | 58.892 | 9.7 | 34.42 |
| enc_hd | pyav | 23.0 | 77.978 | 19.6 | 34.11 |
| enc_hd | pyav | 25.0 | 110.994 | 47.1 | 33.94 |
| enc_sd | opencv | 51.0 | 532.718 | 7.2 | 36.08 |
| enc_sd | opencv | 55.0 | 524.032 | 7.2 | 36.08 |
| enc_sd | opencv | 59.0 | 529.999 | 7.2 | 36.08 |
| enc_sd | opencv | 63.0 | 528.295 | 7.2 | 36.08 |
| enc_sd | opencv | 67.0 | 527.904 | 7.2 | 36.08 |
| enc_sd | pvio_cpu | 17.0 | 77.861 | 2.1 | 35.5 |
| enc_sd | pvio_cpu | 19.0 | 101.117 | 4.5 | 35.04 |
| enc_sd | pvio_cpu | 21.0 | 137.544 | 10.3 | 34.79 |
| enc_sd | pvio_cpu | 23.0 | 182.336 | 20.7 | 34.37 |
| enc_sd | pvio_cpu | 25.0 | 256.905 | 48.5 | 33.88 |
| enc_sd | pvio_gpu | 17.0 | 319.276 | 6.1 | 35.35 |
| enc_sd | pvio_gpu | 19.0 | 302.701 | 14.1 | 35.16 |
| enc_sd | pvio_gpu | 21.0 | 300.85 | 37.4 | 34.75 |
| enc_sd | pvio_gpu | 23.0 | 308.0 | 52.3 | 34.35 |
| enc_sd | pvio_gpu | 25.0 | 301.37 | 75.3 | 34.16 |
| enc_sd | pyav | 17.0 | 57.795 | 2.1 | 35.03 |
| enc_sd | pyav | 19.0 | 76.303 | 4.5 | 34.58 |
| enc_sd | pyav | 21.0 | 109.728 | 10.3 | 34.35 |
| enc_sd | pyav | 23.0 | 142.045 | 20.6 | 34.03 |
| enc_sd | pyav | 25.0 | 192.614 | 47.3 | 33.8 |

## Random access (frames/s, higher better)

| workload | decord_cpu | opencv_cpu | pvio_cpu | pvio_gpu | pyav_cpu | torchcodec_cpu | torchcodec_cuda |
| --- | --- | --- | --- | --- | --- | --- | --- |
| fhd_h264 | 31.0 | 3.0 | 22.0 | 125.0 | 6.0 | 35.0 | 137.0 |
| hd_h264 | 70.0 | 7.0 | 51.0 | 238.0 | 13.0 | 76.0 | 273.0 |
| sd_h264 | 154.0 | 17.0 | 106.0 | 430.0 | 29.0 | 162.0 | 508.0 |

## Seek correctness (all videos)

| backend | x_seek_correct |
| --- | --- |
| decord_cpu | True |
| opencv_cpu | True |
| pvio_cpu | True |
| pvio_gpu | True |
| pyav_cpu | True |
| torchcodec_cpu | True |
| torchcodec_cuda | True |

## Sequential access (frames/s, higher better)

| workload | dali_gpu | decord_cpu | opencv_cpu | pvio_cpu | pvio_gpu | pyav_cpu | torchcodec_cpu | torchcodec_cuda |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fhd_h264 | 27.0 | 91.0 | 99.0 | 62.0 | 556.0 | 113.0 | 101.0 | 564.0 |
| hd_h264 | 56.0 | 211.0 | 236.0 | 170.0 | 1136.0 | 266.0 | 236.0 | 1127.0 |
| sd_h264 | 104.0 | 458.0 | 552.0 | 444.0 | 2106.0 | 613.0 | 529.0 | 2125.0 |
