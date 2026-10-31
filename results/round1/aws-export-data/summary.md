## AWS-side results `restricted-round1`

Window **2026-10-24 20:01** to **2026-10-24 20:46 MDT** (Calgary; 02:01–02:46 UTC). One row per run. A new run starts after 30 s with no requests. Duration figures skip each run's first **30 s** (warm-up). Run start times are Calgary time.

### Execution duration (ms, warm-up excluded)

| Function | Run start (Calgary) | Length (s) | Requests measured | Mean | p50 | p95 | p99 | Max |
|---|---|--:|--:|--:|--:|--:|--:|--:|
| `seng533-data-512` | 2026-10-24 20:01:32 | 148 | 240 | 1435.9 | 1417.8 | 1523.3 | 1544.6 | 1554.1 |
| `seng533-api-1769` | 2026-10-24 20:12:10 | 150 | 9577 | 1.4 | 1.4 | 1.7 | 2.2 | 9.5 |
| `seng533-api-512` | 2026-10-24 20:15:21 | 150 | 9573 | 1.9 | 1.6 | 2.8 | 6.3 | 51.3 |
| `seng533-cpu-1024` | 2026-10-24 20:18:32 | 150 | 787 | 1178.2 | 1181.4 | 1222.8 | 1230 | 1252.4 |
| `seng533-data-1024` | 2026-10-24 20:21:44 | 149 | 446 | 750.8 | 693 | 921.1 | 928.1 | 941.2 |
| `seng533-cpu-1024` | 2026-10-24 20:24:55 | 150 | 292 | 1192 | 1186.5 | 1228.2 | 1237.4 | 1256 |
| `seng533-cpu-1024` | 2026-10-24 20:28:07 | 149 | 94 | 1214.6 | 1214.8 | 1230.5 | 1257.3 | 1259.6 |
| `seng533-api-1024` | 2026-10-24 20:31:17 | 149 | 9451 | 1.6 | 1.5 | 1.8 | 2.4 | 20.1 |
| `seng533-cpu-512` | 2026-10-24 20:34:29 | 149 | 146 | 2413.7 | 2418.8 | 2484.4 | 2500.4 | 2524.1 |
| `seng533-cpu-1769` | 2026-10-24 20:37:40 | 149 | 457 | 732.3 | 757.2 | 768.7 | 771.5 | 792.4 |
| `seng533-data-1769` | 2026-10-24 20:40:51 | 149 | 804 | 391.6 | 387.4 | 419.1 | 430.3 | 454.2 |

### Cold starts, capacity and cost (whole run)

| Function | Run start (Calgary) | Requests | Cold starts | Init mean (ms) | Environments | Peak concurrency | Throttles | Errors / timeouts | Max memory used (MB) | Billed mean (ms) | Cost per 1M req (USD) |
|---|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| `seng533-data-512` | 2026-10-24 20:01:32 | 302 | 3 | 546.9 | 3 | 3 | 0 | 0 | 132 / 512 | 1436.4 | 12.17 |
| `seng533-api-1769` | 2026-10-24 20:12:10 | 11845 | 3 | 78.3 | 3 | 3 | 0 | 0 | 34 / 1769 | 1.9 | 0.26 |
| `seng533-api-512` | 2026-10-24 20:15:21 | 11984 | 4 | 95.5 | 4 | 4 | 0 | 0 | 34 / 512 | 2.3 | 0.22 |
| `seng533-cpu-1024` | 2026-10-24 20:18:32 | 988 | 8 | 90.2 | 8 | 9 | 0 | 0 | 33 / 1024 | 1178.7 | 19.85 |
| `seng533-data-1024` | 2026-10-24 20:21:44 | 559 | 3 | 552.3 | 3 | 3 | 0 | 0 | 132 / 1024 | 751.3 | 12.72 |
| `seng533-cpu-1024` | 2026-10-24 20:24:55 | 366 | 0 | – | 3 | 3 | 0 | 0 | 34 / 1024 | 1192.5 | 20.08 |
| `seng533-cpu-1024` | 2026-10-24 20:28:07 | 118 | 0 | – | 1 | 1 | 0 | 0 | 34 / 1024 | 1215.1 | 20.45 |
| `seng533-api-1024` | 2026-10-24 20:31:17 | 11798 | 3 | 81.8 | 3 | 3 | 0 | 0 | 34 / 1024 | 2 | 0.23 |
| `seng533-cpu-512` | 2026-10-24 20:34:29 | 184 | 3 | 91.7 | 3 | 4 | 0 | 0 | 33 / 512 | 2414.2 | 20.32 |
| `seng533-cpu-1769` | 2026-10-24 20:37:40 | 574 | 3 | 86 | 3 | 3 | 0 | 0 | 33 / 1769 | 732.9 | 21.30 |
| `seng533-data-1769` | 2026-10-24 20:40:51 | 1004 | 3 | 563.9 | 3 | 3 | 0 | 0 | 132 / 1769 | 392.1 | 11.49 |

<details><summary>What the columns mean</summary>

- **Execution duration**: time Lambda spent running the handler (REPORT `Duration`), excluding network and Function URL overhead. Client-side response time and throughput come from k6, not from here.
- **† Short run**: shorter than the warm-up, so every request is included.
- **⚠️ Long run**: over 180 s, so two runs on the same function were probably less than 30 s apart and got merged. For exact per-run numbers, join the CSV with k6 results on the `x-amzn-requestid` response header (= `request_id`).
- **Cold starts**: requests with an `Init Duration`, meaning a new execution environment was created. **Environments**: distinct log streams (one per environment).
- **Peak concurrency / Throttles**: CloudWatch 1-minute `ConcurrentExecutions` (max) and `Throttles` (sum) for the minutes overlapping the run. Throttles are requests rejected with HTTP 429.
- **Cost per 1M requests**: mean billed duration x memory x $1.66667e-05/GB-s + $0.20/1M requests (x86 on-demand list price, no free tier). It uses requests after the warm-up; billed duration includes init time on cold starts.
- Raw per-request data (CSV) and 1-minute metrics are in the run's artifact.

</details>
