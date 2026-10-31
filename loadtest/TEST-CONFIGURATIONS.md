# Test configurations

Exactly what runs when you start a round. Values come from `run.js`, `round.sh` and `config/experiment.json`.

## One round = 11 runs

`./loadtest/round.sh restricted <1|2|3>` runs **11 setups once each**, in a **new random order** every round, **one at a time**, with a **40 s pause** between runs. **3 rounds on separate days = 33 runs.**

**User counts:** the AWS account is limited to 10 requests at once and 100 per second, and AWS rejected the increase. So instead of the proposal's 10 users (and 1 / 10 / 50 for RQ2), we use **3 users** (and **1 / 3 / 8** for RQ2). This is a plan adjustment.

The research questions share runs: `cpu-1024` is used by all three, and `api-1024` and `data-1024` by both RQ1 and RQ3. That's why 15 table rows below are only 11 setups.

### RQ1: How does memory affect response time and successful throughput?
Memory varies; users fixed at 3.

| Setup | Workload | Memory | Users |
|---|---|---|---|
| `api-512` | api | 512 MB | 3 |
| `api-1024` | api | 1024 MB | 3 |
| `api-1769` | api | 1769 MB | 3 |
| `cpu-512` | cpu | 512 MB | 3 |
| `cpu-1024` | cpu | 1024 MB | 3 |
| `cpu-1769` | cpu | 1769 MB | 3 |
| `data-512` | data | 512 MB | 3 |
| `data-1024` | data | 1024 MB | 3 |
| `data-1769` | data | 1769 MB | 3 |

### RQ2: How does the number of users at once affect mean, p95 and p99 response time?
Users vary; cpu workload, memory fixed at 1024 MB.

| Setup | Workload | Memory | Users |
|---|---|---|---|
| `cpu-1024-low` | cpu | 1024 MB | 1 |
| `cpu-1024` | cpu | 1024 MB | 3 |
| `cpu-1024-high` | cpu | 1024 MB | 8 |

### RQ3: How do workload types compare under the same memory and users?
Workload varies; memory fixed at 1024 MB, users at 3.

| Setup | Workload | Memory | Users |
|---|---|---|---|
| `api-1024` | api | 1024 MB | 3 |
| `cpu-1024` | cpu | 1024 MB | 3 |
| `data-1024` | data | 1024 MB | 3 |

## Every run (identical apart from the setup)

| Parameter | Value |
|---|---|
| k6 executor | `constant-vus`: the same number of users for the whole run, no ramp-up |
| Duration | **150 s** = **30 s warm-up** + **120 s measurement** |
| Warm-up | Requests **sent** in the first 30 s are tagged `phase: warmup` and excluded from results; the rest are `phase: measure` |
| Think time | **0**: each user sends its next request as soon as the previous one returns (closed system) |
| Request | `POST <function URL>`, header `content-type: application/json` |
| Body (all workloads) | `{"user_id": "u-1", "item": "widget", "quantity": 3}` |
| Client timeout | 60 s (longer than the 30 s Lambda timeout, so Lambda timeouts show up as 5xx, not client timeouts) |
| Counted as successful | Status **200**, and `ok == true`, and the right `workload` and `memory_mb`, and `result` equals the expected answer below |
| Recorded per request | Send time, phase, user, status, error code, response time (`http_req_duration`), success, AWS request ID, instance ID, cold start, function work time |

## What each workload computes (fixed, `frozen: true`)

| Workload | Work per request | Expected answer |
|---|---|---|
| api | Validates the request fields and echoes them back | `{"user_id": "u-1", "item": "widget", "quantity": 3}` |
| cpu | Counts primes ≤ **500,000** by trial division | `{"prime_count": 41538}` |
| data | Sorts **300,000** records (generated once per instance with seed **533**), keeps values ≥ 500, and computes count, min, max, mean, per-category counts and a checksum | Full values in `config/experiment.json` → `expected_results.data` |

## Lambda configuration (same for every function)

Region **us-west-2**, Python **3.12**, **x86_64**, timeout **30 s**, ephemeral storage **512 MB**, no reserved or provisioned concurrency, X-Ray off. Each setup's function has its own **Function URL** (auth `NONE`, `BUFFERED`, no API Gateway or VPC). Only the memory differs between functions of the same workload.

## Not part of the study

`./loadtest/run.sh test <setup>` is a **20 s check with 1 user** (5 s warm-up), saved to `results/test/`, which git ignores. Its results are never used.
