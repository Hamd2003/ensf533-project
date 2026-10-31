## AWS-side results `restricted-round2`

Window **2026-10-31 14:13** to **2026-10-31 14:52 MDT** (Calgary; 20:13–20:52 UTC). One row per run. A new run starts after 30 s with no requests. Duration figures skip each run's first **30 s** (warm-up). Run start times are Calgary time.

### Execution duration (ms, warm-up excluded)

| Function | Run start (Calgary) | Length (s) | Requests measured | Mean | p50 | p95 | p99 | Max |
|---|---|--:|--:|--:|--:|--:|--:|--:|
| `seng533-data-1024` | 2026-10-31 14:14:00 | 149 | 509 | 668 | 669.2 | 704.2 | 717 | 737.3 |
| `seng533-cpu-1024` | 2026-10-31 14:17:11 | 150 | 790 | 1181.1 | 1176.3 | 1236.9 | 1247.9 | 1268.8 |
| `seng533-data-512` | 2026-10-31 14:20:23 | 148 | 239 | 1461.7 | 1462.3 | 1506.1 | 1524.7 | 1599.4 |
| `seng533-data-1769` | 2026-10-31 14:23:33 | 149 | 843 | 389.7 | 385.3 | 415.4 | 434.8 | 505.9 |
| `seng533-api-1769` | 2026-10-31 14:26:43 | 150 | 10596 | 1.6 | 1.5 | 2.2 | 3.8 | 32.5 |
| `seng533-cpu-1769` | 2026-10-31 14:29:54 | 149 | 500 | 681.9 | 679 | 696.1 | 714.4 | 756.1 |
| `seng533-api-512` | 2026-10-31 14:33:04 | 150 | 10309 | 1.7 | 1.6 | 2.2 | 4.6 | 37.8 |
| `seng533-cpu-1024` | 2026-10-31 14:36:16 | 149 | 105 | 1108.8 | 1107.3 | 1124.7 | 1127.3 | 1127.3 |
| `seng533-cpu-1024` | 2026-10-31 14:39:27 | 148 | 301 | 1150.9 | 1110.8 | 1252.5 | 1259.5 | 1268.4 |
| `seng533-cpu-512` | 2026-10-31 14:42:39 | 149 | 154 | 2319.7 | 2361 | 2515.2 | 2543.2 | 2552 |
| `seng533-api-1024` | 2026-10-31 14:45:49 | 149 | 10786 | 1.5 | 1.5 | 2 | 3 | 241.7 |

### Cold starts, capacity and cost (whole run)

| Function | Run start (Calgary) | Requests | Cold starts | Init mean (ms) | Environments | Peak concurrency | Throttles | Errors / timeouts | Max memory used (MB) | Billed mean (ms) | Cost per 1M req (USD) |
|---|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| `seng533-data-1024` | 2026-10-31 14:14:00 | 639 | 3 | 550.5 | 3 | 3 | 0 | 0 | 132 / 1024 | 668.5 | 11.34 |
| `seng533-cpu-1024` | 2026-10-31 14:17:11 | 992 | 8 | 114.1 | 8 | 9 | 0 | 0 | 34 / 1024 | 1181.6 | 19.89 |
| `seng533-data-512` | 2026-10-31 14:20:23 | 301 | 3 | 567.3 | 3 | 4 | 0 | 0 | 132 / 512 | 1462.2 | 12.39 |
| `seng533-data-1769` | 2026-10-31 14:23:33 | 1058 | 3 | 551.8 | 3 | 3 | 0 | 0 | 132 / 1769 | 390.2 | 11.44 |
| `seng533-api-1769` | 2026-10-31 14:26:43 | 13202 | 3 | 87.7 | 3 | 3 | 0 | 0 | 34 / 1769 | 2.1 | 0.26 |
| `seng533-cpu-1769` | 2026-10-31 14:29:54 | 628 | 3 | 96.2 | 3 | 3 | 0 | 0 | 34 / 1769 | 682.4 | 19.85 |
| `seng533-api-512` | 2026-10-31 14:33:04 | 12843 | 3 | 105.8 | 3 | 3 | 0 | 0 | 34 / 512 | 2.2 | 0.22 |
| `seng533-cpu-1024` | 2026-10-31 14:36:16 | 132 | 1 | 114.5 | 1 | 1 | 0 | 0 | 34 / 1024 | 1109.3 | 18.69 |
| `seng533-cpu-1024` | 2026-10-31 14:39:27 | 379 | 2 | 80.1 | 3 | 3 | 0 | 0 | 34 / 1024 | 1151.4 | 19.39 |
| `seng533-cpu-512` | 2026-10-31 14:42:39 | 192 | 4 | 100.6 | 4 | 4 | 0 | 0 | 34 / 512 | 2320.6 | 19.54 |
| `seng533-api-1024` | 2026-10-31 14:45:49 | 13394 | 4 | 83.9 | 4 | 4 | 0 | 0 | 34 / 1024 | 2 | 0.23 |

<details><summary>What the columns mean</summary>

- **Execution duration**: time Lambda spent running the handler (REPORT `Duration`), excluding network and Function URL overhead. Client-side response time and throughput come from k6, not from here.
- **† Short run**: shorter than the warm-up, so every request is included.
- **⚠️ Long run**: over 180 s, so two runs on the same function were probably less than 30 s apart and got merged. For exact per-run numbers, join the CSV with k6 results on the `x-amzn-requestid` response header (= `request_id`).
- **Cold starts**: requests with an `Init Duration`, meaning a new execution environment was created. **Environments**: distinct log streams (one per environment).
- **Peak concurrency / Throttles**: CloudWatch 1-minute `ConcurrentExecutions` (max) and `Throttles` (sum) for the minutes overlapping the run. Throttles are requests rejected with HTTP 429.
- **Cost per 1M requests**: mean billed duration x memory x $1.66667e-05/GB-s + $0.20/1M requests (x86 on-demand list price, no free tier). It uses requests after the warm-up; billed duration includes init time on cold starts.
- Raw per-request data (CSV) and 1-minute metrics are in the run's artifact.

</details>
