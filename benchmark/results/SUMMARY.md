# Benchmark summary

## Encoding (frames/s, compression ratio = JPEG-folder/video, quality)

| workload | backend | metric_main | x_compression_ratio | x_file_size_mb | x_psnr_db | x_ssim |
| --- | --- | --- | --- | --- | --- | --- |
| enc_hd | opencv | 216.175 | 7.4 | 5.01 | 36.09 | 0.886 |
| enc_hd | pvio_cpu | 59.191 | 6.6 | 5.61 | 35.07 | 0.861 |
| enc_hd | pvio_gpu | 203.128 | 26.8 | 1.38 | 34.94 | 0.862 |
| enc_hd | pyav | 46.895 | 6.6 | 5.64 | 34.53 | 0.851 |
| enc_sd | opencv | 503.91 | 7.1 | 2.31 | 36.06 | 0.886 |
| enc_sd | pvio_cpu | 111.561 | 6.8 | 2.42 | 34.91 | 0.857 |
| enc_sd | pvio_gpu | 198.132 | 27.0 | 0.61 | 34.96 | 0.863 |
| enc_sd | pyav | 83.352 | 6.7 | 2.44 | 34.42 | 0.849 |

## Encoding Pareto sweep (throughput vs compression per quality level)

| workload | backend | x_quality_param | metric_main | x_compression_ratio | x_psnr_db |
| --- | --- | --- | --- | --- | --- |
| enc_hd | opencv | 51.0 | 221.35 | 7.4 | 36.09 |
| enc_hd | opencv | 55.0 | 224.481 | 7.4 | 36.09 |
| enc_hd | opencv | 59.0 | 225.849 | 7.4 | 36.09 |
| enc_hd | opencv | 63.0 | 218.028 | 7.4 | 36.09 |
| enc_hd | opencv | 67.0 | 220.953 | 7.4 | 36.09 |
| enc_hd | pvio_cpu | 17.0 | 38.663 | 2.1 | 35.62 |
| enc_hd | pvio_cpu | 19.0 | 50.764 | 4.4 | 35.16 |
| enc_hd | pvio_cpu | 21.0 | 69.63 | 9.7 | 34.94 |
| enc_hd | pvio_cpu | 23.0 | 91.932 | 19.7 | 34.51 |
| enc_hd | pvio_cpu | 25.0 | 131.142 | 48.1 | 34.09 |
| enc_hd | pvio_gpu | 17.0 | 151.626 | 6.1 | 35.33 |
| enc_hd | pvio_gpu | 19.0 | 200.559 | 14.1 | 35.15 |
| enc_hd | pvio_gpu | 21.0 | 203.862 | 38.9 | 34.75 |
| enc_hd | pvio_gpu | 23.0 | 202.167 | 53.9 | 34.37 |
| enc_hd | pvio_gpu | 25.0 | 201.067 | 80.3 | 34.19 |
| enc_hd | pyav | 17.0 | 30.125 | 2.1 | 35.07 |
| enc_hd | pyav | 19.0 | 40.713 | 4.4 | 34.63 |
| enc_hd | pyav | 21.0 | 56.459 | 9.8 | 34.4 |
| enc_hd | pyav | 23.0 | 74.317 | 19.9 | 34.08 |
| enc_hd | pyav | 25.0 | 106.44 | 48.5 | 33.91 |
| enc_sd | opencv | 51.0 | 508.296 | 7.1 | 36.06 |
| enc_sd | opencv | 55.0 | 494.535 | 7.1 | 36.06 |
| enc_sd | opencv | 59.0 | 481.87 | 7.1 | 36.06 |
| enc_sd | opencv | 63.0 | 487.114 | 7.1 | 36.06 |
| enc_sd | opencv | 67.0 | 476.795 | 7.1 | 36.06 |
| enc_sd | pvio_cpu | 17.0 | 74.989 | 2.1 | 35.47 |
| enc_sd | pvio_cpu | 19.0 | 93.342 | 4.5 | 35.0 |
| enc_sd | pvio_cpu | 21.0 | 128.337 | 10.1 | 34.77 |
| enc_sd | pvio_cpu | 23.0 | 172.877 | 20.2 | 34.28 |
| enc_sd | pvio_cpu | 25.0 | 239.54 | 47.1 | 33.83 |
| enc_sd | pvio_gpu | 17.0 | 202.159 | 6.2 | 35.35 |
| enc_sd | pvio_gpu | 19.0 | 299.874 | 14.3 | 35.16 |
| enc_sd | pvio_gpu | 21.0 | 307.698 | 38.7 | 34.77 |
| enc_sd | pvio_gpu | 23.0 | 306.247 | 51.7 | 34.34 |
| enc_sd | pvio_gpu | 25.0 | 307.164 | 74.0 | 34.15 |
| enc_sd | pyav | 17.0 | 54.24 | 2.1 | 34.98 |
| enc_sd | pyav | 19.0 | 71.864 | 4.5 | 34.53 |
| enc_sd | pyav | 21.0 | 97.469 | 10.1 | 34.28 |
| enc_sd | pyav | 23.0 | 131.894 | 20.1 | 33.96 |
| enc_sd | pyav | 25.0 | 185.466 | 46.2 | 33.7 |

## Random access (frames/s, higher better)

| workload | decord_cpu | opencv_cpu | pvio_cpu | pvio_gpu | pyav_cpu | torchcodec_cpu | torchcodec_cuda |
| --- | --- | --- | --- | --- | --- | --- | --- |
| fhd_h264 | 78.0 | 10.0 | 20.0 | 117.0 | 6.0 | 31.0 | 129.0 |
| hd_h264 | 172.0 | 22.0 | 46.0 | 228.0 | 12.0 | 69.0 | 266.0 |
| sd_h264 | 359.0 | 46.0 | 109.0 | 415.0 | 27.0 | 149.0 | 503.0 |

## Seek correctness (all videos)

| backend | x_seek_correct |
| --- | --- |
| decord_cpu | False |
| opencv_cpu | False |
| pvio_cpu | False |
| pvio_gpu | False |
| pyav_cpu | False |
| torchcodec_cpu | False |
| torchcodec_cuda | False |

## Sequential access (frames/s, higher better)

| workload | dali_gpu | decord_cpu | opencv_cpu | pvio_cpu | pvio_gpu | pyav_cpu | torchcodec_cpu | torchcodec_cuda |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fhd_h264 | 27.0 | 393.0 | 499.0 | 67.0 | 564.0 | 113.0 | 101.0 | 577.0 |
| hd_h264 | 55.0 | 884.0 | 1199.0 | 160.0 | 1130.0 | 253.0 | 227.0 | 1157.0 |
| sd_h264 | 104.0 | 1676.0 | 2542.0 | 425.0 | 1995.0 | 577.0 | 503.0 | 1956.0 |
