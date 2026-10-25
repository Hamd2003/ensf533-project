# Load-test interface (AWS side)

What the load-test scripts need to know to call the Lambda functions and get AWS-side data. This file is public: it contains **no Function URLs**. The AWS owner (GitHub `Hamd2003`) shares the URLs privately in the group chat.

## Endpoints

Nine functions, one per workload × memory cell, all in region `us-west-2` (see `config/experiment.json`):

| Function name | Workload | Memory (MB) |
|---|---|---|
| `seng533-api-512` | api | 512 |
| `seng533-api-1024` | api | 1024 |
| `seng533-api-1769` | api | 1769 |
| `seng533-cpu-512` | cpu | 512 |
| `seng533-cpu-1024` | cpu | 1024 |
| `seng533-cpu-1769` | cpu | 1769 |
| `seng533-data-512` | data | 512 |
| `seng533-data-1024` | data | 1024 |
| `seng533-data-1769` | data | 1769 |

Each function has its own URL. URLs stay the same across normal deploys. If one ever changes (a function is replaced), you'll get the new list privately.

**Never put a URL in a commit, issue, PR, workflow input or anything else public.** Keep them in a gitignored file (`urls.json` and `.env*` are already ignored) or in environment variables.

## Calling a function

Plain HTTPS `POST`, no auth headers, same body for all three workloads (also in `config/experiment.json` → `request_body`):

```sh
curl -X POST -H "content-type: application/json" \
  -d '{"user_id":"u-1","item":"widget","quantity":3}' "$URL"
```

Anything other than `POST` returns `405` without doing any work.

## Validating a response

A request counts as successful only if **all** of these hold:

- HTTP status `200`
- `ok == true`
- `workload` and `memory_mb` match the function you meant to call
- `result` deep-equals `expected_results[<workload>]` in `config/experiment.json`

Example body:

```json
{
  "ok": true,
  "workload": "cpu",
  "memory_mb": 1024,
  "result": {"prime_count": 41538},
  "compute_ms": 512.3,
  "env_id": "3f2a…",
  "cold": false
}
```

| Field | Meaning |
|---|---|
| `compute_ms` | Time spent in the workload itself, measured inside the function. |
| `env_id` | Random ID of the execution environment (one per Lambda instance). The number of distinct values ≈ number of environments used. |
| `cold` | `true` only on the first request an environment serves (a cold start). |

Error responses have `ok: false` and an `error` message. Status codes you may see:

| Status | Meaning |
|---|---|
| `400` | Malformed body (should never happen with the standard body). |
| `405` | Not a `POST`. |
| `429` | Throttled: the account's concurrency quota was hit. This means the limit, **not** a performance result. Tell the AWS owner. |
| `5xx` | Function error or timeout (timeout is 30 s). |

`prime_limit`, `dataset_size` and the expected results are final only once `config/experiment.json` has `"frozen": true`. Runs done before that don't count.

## AWS-side data

1. Wait **at least 10 minutes** after the last run in the window (logs arrive late).
2. GitHub → **Actions → export-aws-data → Run workflow** (branch `main`).
3. Inputs: `start`, the time you clicked play on the first k6 run, in **Calgary time** (`2026-10-28 18:30`, `2026-10-28 6:30pm`, or just `6:30pm` for today; add `Z` for UTC). `end` is optional: leave it empty to include everything up to 10 minutes ago (at most 24 h). Also `functions` (`all` or comma-separated names), `label` (e.g. `round1`) and `warmup` (seconds skipped at the start of each run, default `30`).
4. **Read the results in the run's summary.** There's one row per run per function: execution duration (mean, p50, p95, p99, max) after the warm-up, cold starts and init time, environments, peak concurrency, throttles, errors/timeouts, max memory, billed duration and cost per 1M requests.
5. For your own analysis, download the artifact `aws-data-<label>` (kept 90 days). It holds the same summary (`summary.md`, `summary.json`) plus the raw data below.

**How runs are detected:** a function's traffic is split into runs wherever it gets no requests for **30 s**. If two runs on the **same function** are less than 30 s apart, they merge into one row flagged ⚠️ (longer than 180 s). To avoid that, leave at least 30 s between runs, or export each run with its own window.

Export each round within **15 days**: CloudWatch keeps 1-minute metrics only that long.

The artifact also contains, for each function:

**`<function>.report.csv`**: one row per invocation (from the Lambda `REPORT` log line):

| Column | Meaning |
|---|---|
| `timestamp` | When the REPORT line was logged (UTC, end of the invocation). The summary shows Calgary time. |
| `request_id` | Lambda request ID. |
| `duration_ms` | Execution duration. |
| `billed_ms` | Billed duration (rounded up to 1 ms). |
| `memory_mb` | Configured memory. |
| `max_memory_used_mb` | Peak memory of the environment so far. |
| `init_duration_ms` | Cold-start initialization time; empty for warm invocations. |
| `status` | Empty normally; e.g. `timeout` or `error` when the invocation failed. |
| `log_stream` | Log stream name; one stream per execution environment. |

**`<function>.metrics.json`**: CloudWatch metrics at 60 s resolution: `Invocations_Sum`, `Errors_Sum`, `Throttles_Sum`, `Duration_Average`, `Duration_Maximum`, `ConcurrentExecutions_Maximum`, each as `{timestamps, values}`. Minutes with no data are omitted.

**`summary.json`**: the summary table as data. **`manifest.json`**: window, label, warm-up and per-function line counts.

Request IDs in the CSV can't be joined exactly to `env_id`/`cold` in HTTP responses (only approximately, by time), so treat client-side and AWS-side data as separate sources.

## Limits

- Account concurrency quota in `us-west-2`: **to be confirmed** before the 50-VU configuration. If it is below 50, the 50-VU run will see 429s.
- Function timeout: 30 s.

## Coordination

- **During a round:** nothing on the AWS side changes. Any deploy would create fresh environments (cold starts) and contaminate runs.
- Commits that only touch `loadtest/`, `analysis/`, `results/` or docs never trigger a deploy.
