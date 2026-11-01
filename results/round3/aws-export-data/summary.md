## AWS-side results `restricted-round3`

Window **2026-11-01 10:36** to **2026-11-01 12:36 CST** (Calgary; 16:36–18:36 UTC). One row per run. A new run starts after 30 s with no requests. Duration figures skip each run's first **30 s** (warm-up). Run start times are Calgary time.

### Execution duration (ms, warm-up excluded)

| Function | Run start (Calgary) | Length (s) | Requests measured | Mean | p50 | p95 | p99 | Max |
|---|---|--:|--:|--:|--:|--:|--:|--:|
| `seng533-api-512` | 2026-11-01 11:36:30 | 150 | 10513 | 1.6 | 1.5 | 2 | 3.6 | 60.2 |
| `seng533-cpu-1024` | 2026-11-01 11:39:42 | 148 | 95 | 1213.3 | 1210 | 1240.1 | 1248.5 | 1261.5 |
| `seng533-cpu-1769` | 2026-11-01 11:42:52 | 150 | 480 | 713.3 | 707 | 752 | 764.8 | 800.2 |
| `seng533-data-1769` | 2026-11-01 11:46:03 | 149 | 845 | 389.4 | 387.1 | 417 | 445.5 | 497.4 |
| `seng533-cpu-1024` | 2026-11-01 11:49:14 | 150 | 796 | 1171 | 1176.3 | 1203.6 | 1217.8 | 1237.7 |
| `seng533-data-1024` | 2026-11-01 11:52:26 | 149 | 467 | 735.8 | 694.1 | 869.3 | 884.3 | 886.2 |
| `seng533-api-1024` | 2026-11-01 11:55:36 | 150 | 10575 | 1.7 | 1.6 | 2.4 | 5.2 | 26.2 |
| `seng533-api-1769` | 2026-11-01 11:58:46 | 149 | 10252 | 1.7 | 1.6 | 2.3 | 4.4 | 22 |
| `seng533-cpu-512` | 2026-11-01 12:01:59 | 149 | 149 | 2373.1 | 2361.4 | 2463.2 | 2493.9 | 2519.3 |
| `seng533-cpu-1024` | 2026-11-01 12:05:10 | 149 | 300 | 1162.7 | 1178.2 | 1199.7 | 1216.4 | 1231.6 |
| `seng533-data-512` | 2026-11-01 12:08:22 | 149 | 245 | 1429.7 | 1424.8 | 1465.6 | 1496.6 | 1521.8 |

### Cold starts, capacity and cost (whole run)

| Function | Run start (Calgary) | Requests | Cold starts | Init mean (ms) | Environments | Peak concurrency | Throttles | Errors / timeouts | Max memory used (MB) | Billed mean (ms) | Cost per 1M req (USD) |
|---|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| `seng533-api-512` | 2026-11-01 11:36:30 | 13123 | 3 | 83.8 | 3 | 3 | 0 | 0 | 34 / 512 | 2.1 | 0.22 |
| `seng533-cpu-1024` | 2026-11-01 11:39:42 | 120 | 1 | 123.5 | 1 | 2 | 0 | 0 | 33 / 1024 | 1213.9 | 20.43 |
| `seng533-cpu-1769` | 2026-11-01 11:42:52 | 602 | 3 | 99 | 3 | 3 | 0 | 0 | 33 / 1769 | 713.8 | 20.75 |
| `seng533-data-1769` | 2026-11-01 11:46:03 | 1054 | 4 | 573.8 | 4 | 4 | 0 | 0 | 132 / 1769 | 390.6 | 11.45 |
| `seng533-cpu-1024` | 2026-11-01 11:49:14 | 1000 | 8 | 99.5 | 8 | 8 | 0 | 0 | 35 / 1024 | 1171.5 | 19.73 |
| `seng533-data-1024` | 2026-11-01 11:52:26 | 584 | 3 | 539 | 3 | 3 | 0 | 0 | 132 / 1024 | 736.3 | 12.47 |
| `seng533-api-1024` | 2026-11-01 11:55:36 | 13206 | 3 | 93.3 | 3 | 3 | 0 | 0 | 34 / 1024 | 2.2 | 0.24 |
| `seng533-api-1769` | 2026-11-01 11:58:46 | 12823 | 3 | 84.3 | 3 | 3 | 0 | 0 | 34 / 1769 | 2.2 | 0.26 |
| `seng533-cpu-512` | 2026-11-01 12:01:59 | 188 | 4 | 118.6 | 4 | 4 | 0 | 0 | 33 / 512 | 2374.4 | 19.99 |
| `seng533-cpu-1024` | 2026-11-01 12:05:10 | 377 | 3 | 106.9 | 3 | 3 | 0 | 0 | 33 / 1024 | 1163.2 | 19.59 |
| `seng533-data-512` | 2026-11-01 12:08:22 | 308 | 4 | 561.9 | 4 | 4 | 0 | 0 | 131 / 512 | 1432.6 | 12.14 |

<details><summary>What the columns mean</summary>

- **Execution duration**: time Lambda spent running the handler (REPORT `Duration`), excluding network and Function URL overhead. Client-side response time and throughput come from k6, not from here.
- **† Short run**: shorter than the warm-up, so every request is included.
- **⚠️ Long run**: over 180 s, so two runs on the same function were probably less than 30 s apart and got merged. For exact per-run numbers, join the CSV with k6 results on the `x-amzn-requestid` response header (= `request_id`).
- **Cold starts**: requests with an `Init Duration`, meaning a new execution environment was created. **Environments**: distinct log streams (one per environment).
- **Peak concurrency / Throttles**: CloudWatch 1-minute `ConcurrentExecutions` (max) and `Throttles` (sum) for the minutes overlapping the run. Throttles are requests rejected with HTTP 429.
- **Cost per 1M requests**: mean billed duration x memory x $1.66667e-05/GB-s + $0.20/1M requests (x86 on-demand list price, no free tier). It uses requests after the warm-up; billed duration includes init time on cold starts.
- Raw per-request data (CSV) and 1-minute metrics are in the run's artifact.

</details>
