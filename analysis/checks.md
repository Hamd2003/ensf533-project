# Member 1: data and checks

Rebuild from the repository root: `python3 analysis/build_tables.py`.

Processed 33 runs across 3 rounds; 102,119 measured requests. **0 runs flagged for repo-owner review.**

## Checks table

Little's law estimates users as requests / 120 × mean response time / 1000. Deviation is the absolute percentage difference from configured users. Flag a run if deviation exceeds 10% or any request fails.

| Round | Setup | Users | Little's law | Deviation (%) | Failed | Throttled | Function errors | Timeouts | Wrong answers | Other failures | Cold starts | Result |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | api-512 | 3 | 2.974 | 0.86 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | PASS |
| 1 | api-1024 | 3 | 2.973 | 0.88 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | PASS |
| 1 | api-1769 | 3 | 2.975 | 0.83 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | PASS |
| 1 | cpu-512 | 3 | 3.013 | 0.42 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | PASS |
| 1 | cpu-1024 | 3 | 3.003 | 0.09 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | PASS |
| 1 | cpu-1769 | 3 | 3.002 | 0.07 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | PASS |
| 1 | data-512 | 3 | 3.000 | 0.01 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | PASS |
| 1 | data-1024 | 3 | 3.007 | 0.22 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | PASS |
| 1 | data-1769 | 3 | 3.004 | 0.13 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | PASS |
| 1 | cpu-1024-low | 1 | 1.006 | 0.64 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | PASS |
| 1 | cpu-1024-high | 8 | 7.996 | 0.05 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | PASS |
| 2 | api-512 | 3 | 2.972 | 0.94 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | PASS |
| 2 | api-1024 | 3 | 2.973 | 0.89 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | PASS |
| 2 | api-1769 | 3 | 2.970 | 1.00 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | PASS |
| 2 | cpu-512 | 3 | 3.014 | 0.47 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | PASS |
| 2 | cpu-1024 | 3 | 2.993 | 0.24 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | PASS |
| 2 | cpu-1769 | 3 | 2.999 | 0.03 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | PASS |
| 2 | data-512 | 3 | 2.992 | 0.25 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | PASS |
| 2 | data-1024 | 3 | 2.991 | 0.29 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | PASS |
| 2 | data-1769 | 3 | 2.995 | 0.18 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | PASS |
| 2 | cpu-1024-low | 1 | 0.997 | 0.26 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | PASS |
| 2 | cpu-1024-high | 8 | 8.011 | 0.13 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | PASS |
| 3 | api-512 | 3 | 2.965 | 1.18 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | PASS |
| 3 | api-1024 | 3 | 2.969 | 1.03 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | PASS |
| 3 | api-1769 | 3 | 2.964 | 1.21 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | PASS |
| 3 | cpu-512 | 3 | 2.981 | 0.64 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | PASS |
| 3 | cpu-1024 | 3 | 2.995 | 0.16 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | PASS |
| 3 | cpu-1769 | 3 | 3.002 | 0.06 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | PASS |
| 3 | data-512 | 3 | 3.014 | 0.47 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | PASS |
| 3 | data-1024 | 3 | 3.007 | 0.24 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | PASS |
| 3 | data-1769 | 3 | 2.991 | 0.29 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | PASS |
| 3 | cpu-1024-low | 1 | 0.999 | 0.11 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | PASS |
| 3 | cpu-1024-high | 8 | 7.995 | 0.06 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | PASS |

## Calculation notes

- Only `phase == "measure"` requests enter the calculations. AWS records are joined by `request_id` within the corresponding round and function. Missing or duplicate required records stop the build before any output is written.
- Response statistics include all measured requests. Success means `valid == true`; successful throughput divides that count by exactly 120 seconds. Failure rate is a fraction.
- `std_ms` is sample standard deviation (denominator n − 1; zero for one request). p95 and p99 use linear interpolation at rank (n − 1) × percentile.
- `per_config.csv` is the unweighted arithmetic mean of each run's metrics. Requests from separate runs are never pooled. Counts such as cold starts and per-run maxima can therefore have fractional averages. CSV values retain full precision.
- AWS execution, billing and maximum memory use come only from matched measured requests. Overhead is mean response time minus mean AWS execution time. Cost uses the guide's USD formula, including $0.20 per million requests.
- Peak concurrency uses 60-second AWS buckets overlapping the interval from the first measured request send to the last measured response completion. It is a minute-level function metric, so a bucket can include activity outside that interval. Observed peaks are retained even when they exceed configured users.
- Cold starts count measured k6 requests with `cold == true`. Cold starts alone do not flag a run. `other_failures` preserves failures outside the guide's four named types.

## Handoff

Members 2–4 should read `analysis/per_config.csv` for round-average results and `analysis/per_run.csv` for individual runs. Use the checks table above in the midterm report.
