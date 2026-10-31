# Analysis guide: midterm report

**New to this repo? Start here.** What data we have, the rules for using it, and what each member delivers for the **midterm report (Nov 6)**. You write your own code (Python in `analysis/`; pandas and matplotlib are fine). This page tells you what it must produce.

**What the proposal promises for the midterm** (timeline, Oct 31 – Nov 6): *"Preliminary graphs and tables; document hosting, load generator location, and hardware; write individual contributions."* That's what this guide covers.

---

## The study in 30 seconds

We're measuring how fast **AWS Lambda** (code that runs in the cloud) responds under different conditions. A tool called **k6** sent thousands of requests from a laptop to 9 cloud functions and timed every one.

We changed three things:
- **Memory** given to the function: 512, 1024 or 1769 MB.
- **Users at once**, meaning how many requests are in progress at the same time: 1, 3 or 8.
- **Workload:** `api` (tiny job), `cpu` (heavy maths) or `data` (sorting a big list).

That gives **11 test setups**. A **round** runs all 11 once, and we do **3 rounds**, so **33 runs** in total. Each run lasts 150 s: the first **30 s are warm-up and don't count**, and the last **120 s are the measurement**.

Full list of setups: [../loadtest/TEST-CONFIGURATIONS.md](../loadtest/TEST-CONFIGURATIONS.md)

---

## Who does what

We need to decide who will take on what analysis for the midterm report **Member 1 goes first:** everyone else builds on Member 1's two CSV files.

| Role | Delivers | Deadline |
|---|---|---|
| **Member 1: data and checks** | `per_run.csv`, `per_config.csv`, the checks table | **Nov 2** |
| **Member 2: RQ1 (memory)** | Graphs 1–2, the RQ1 supporting table, plus a summary paragraph | Nov 4 |
| **Member 3: RQ2 (users at once)** | Graph 3, the main results table, plus a summary paragraph | Nov 4 |
| **Member 4: RQ3 (workload type)** | Graphs 4–5, the RQ3 supporting table, the load-generator details, plus a summary paragraph | Nov 4 |
| **Repo owner (AWS side)** | Rounds 2 and 3 with their AWS exports in `results/`; the hosting details (AWS setup) and plan adjustments | ASAP |
| **Everyone** | Their own individual contribution | Nov 5 |

The detailed task for each member is below the shared sections.

---

## What everyone needs to know

### The data files

Each round has a folder, `results/round1/`, `results/round2/` and `results/round3/`, with two subfolders:

| File | What it is | Needed? |
|---|---|---|
| `k6-measured-data/restricted-r<N>-<setup>.jsonl` | **k6 data:** one JSON line per request, timed from the laptop | **Yes, the main data** |
| `aws-export-data/seng533-<function>.report.csv` | **AWS data:** one row per request, measured inside AWS | **Yes**, for execution time, cost and memory |
| `aws-export-data/seng533-<function>.metrics.json` | Per-minute AWS counters | Only for peak concurrency |
| `aws-export-data/summary.md` | Readable per-run summary from AWS | Optional quick look |
| `k6-measured-data/restricted-r<N>-<setup>.html` | k6's own graph report | No |
| `k6-measured-data/restricted-r<N>-order.txt`, `aws-export-data/summary.json`, `manifest.json` | Run order, machine-readable copies | No |

**k6 line (`.jsonl`)**, example:
```json
{"setup":"cpu-1024","vus":3,"phase":"measure","status":200,"duration_ms":1240.3,"valid":true,"request_id":"040a4ea7-…","cold":false, …}
```

| Field | Plain meaning |
|---|---|
| `setup` | Which of the 11 setups, e.g. `cpu-1024` |
| `vus` | Users at once in this run |
| `phase` | `warmup` = ignore it; `measure` = use it |
| `status` | `200` = OK, `429` = AWS refused (too busy), `5xx` = function failed, `0` = no answer |
| `duration_ms` | **Response time** in milliseconds, the main number of the study |
| `valid` | `true` = the request succeeded **and** the answer was correct |
| `request_id` | AWS's ID for this request; matches the same request in the AWS file |
| `cold` | `true` = this request started a fresh Lambda instance (slower) |

The round number isn't inside the lines; it's in the folder name (`round1`, …).

**AWS row (`.report.csv`)**:

| Column | Plain meaning |
|---|---|
| `request_id` | Same ID as in the k6 line |
| `duration_ms` | **Execution time:** how long the function itself ran, with no network |
| `billed_ms` | Time AWS charges for |
| `memory_mb` / `max_memory_used_mb` | Memory given / memory actually used |
| `init_duration_ms` | Only on cold starts: how long the new instance took to set up |

**Linking k6 and AWS:** match rows on `request_id`. Every k6 request has exactly one AWS row. AWS files are named by **function**, so `cpu-1024-low`, `cpu-1024` and `cpu-1024-high` all sit in `seng533-cpu-1024.report.csv`. Matching on `request_id` sorts them back into their setups.

### Rules everyone follows

1. **Use only `phase == "measure"` requests.** Never include the warm-up.
2. **Calculate per run first** (one round + one setup), **then** average the rounds. Never pool requests from different runs into one list.
3. **Successful** = `valid == true`. **Throughput** = successful requests ÷ **120 s**.
4. **Failure types** (proposal: throttles, function errors and timeouts, plus "served incorrectly"):
   - **throttled** = `status` 429;
   - **function error** = `status` 500–599 whose AWS `status` column isn't `timeout`;
   - **timeout** = `status` 500–599 whose AWS `status` is `timeout`, or `status` 0 (no answer reached the laptop);
   - **wrong answer** = `status` 200 but `valid == false`.
5. **Network delay** = k6 `duration_ms` − AWS `duration_ms`, for the same request.
6. **Cost per 1M requests (USD)** = mean `billed_ms` ÷ 1000 × `memory_mb` ÷ 1024 × 0.0000166667 × 1,000,000 + 0.20.
7. **Read numbers from Member 1's CSV files**, not the raw files, so every graph uses the same calculations.
8. **Save graphs as PNG** in `analysis/figures/`, named `graph<N>_<short-name>.png`.
9. **Response times run from about 40 ms (`api`) to about 2,500 ms (`cpu-512`).** Use a **log scale** when workloads share an axis.

---

## Member 1: data and checks (goes first)

**Goal:** turn the raw files into two clean tables everyone else uses, plus a checks table.

**Build** `analysis/build_tables.py`. It reads every `results/round*/` folder, so re-running it after each new round updates everything.

**Output 1: `analysis/per_run.csv`**, one row per run (11 per round):

| Column | Definition |
|---|---|
| `round`, `setup` | Which run |
| `workload`, `memory_mb`, `users` | From the setup (`workload` = text before the first `-`) |
| `requests` | Number of `measure` requests |
| `mean_ms`, `median_ms`, `std_ms`, `p95_ms`, `p99_ms` | Of k6 `duration_ms` |
| `successful`, `throughput_rps`, `failure_rate` | Rule 3; `failure_rate` = 1 − successful ÷ requests |
| `throttled`, `function_errors`, `timeouts`, `wrong_answers` | Counts per rule 4 |
| `exec_mean_ms` | Mean AWS `duration_ms` |
| `overhead_ms` | `mean_ms` − `exec_mean_ms` |
| `billed_mean_ms`, `cost_per_million_usd` | Rule 6 |
| `max_memory_used_mb` | Largest AWS `max_memory_used_mb` |
| `cold_starts` | `measure` requests with `cold == true` |
| `peak_concurrency` | Largest `ConcurrentExecutions_Maximum` in that function's `metrics.json` during the run's minutes |
| `littles_law` | requests ÷ 120 × `mean_ms` ÷ 1000 |

**Output 2: `analysis/per_config.csv`**, one row per setup (11): `setup, workload, memory_mb, users`, then the **average over the rounds** of: `mean_ms, median_ms, std_ms, p95_ms, p99_ms, throughput_rps, failure_rate, exec_mean_ms, overhead_ms, max_memory_used_mb, cost_per_million_usd, cold_starts, peak_concurrency`.

**Output 3: checks table** (in the report): per run, `littles_law` vs `users`, the failure counts and `cold_starts`. **Flag any run where `littles_law` is more than 10% off `users`, or with failures**, and tell the repo owner, who will redo it.

**Done when** your numbers for Round 1 match these reference values (rounded):

| Setup | `requests` | `mean_ms` | `p95_ms` | `throughput_rps` | `exec_mean_ms` | `cost_per_million_usd` | `littles_law` |
|---|---|---|---|---|---|---|---|
| `api-512` | 9,601 | 37.2 | 43.1 | 80.0 | 1.9 | 0.22 | 2.97 |
| `cpu-1024` | 292 | 1,234.0 | 1,287.5 | 2.43 | 1,192.0 | 20.1 | 3.00 |
| `cpu-1024-high` | 787 | 1,219.2 | 1,264.1 | 6.56 | 1,178.2 | 19.9 | 8.00 |
| `data-512` | 243 | 1,481.4 | 1,585.4 | 2.02 | 1,435.9 | 12.2 | 3.00 |

…plus `failure_rate` = 0 for every Round 1 run, and `cold_starts` = 1 only for `api-512`. Small differences in p95 are fine, because percentile methods differ slightly.

---

## Member 2: RQ1, does more memory make it faster?

**Uses:** the 9 setups `api-*`, `cpu-*` and `data-*`, **not** `cpu-1024-low` or `cpu-1024-high`. Read `per_config.csv`.

**Build** `analysis/rq1_memory.py`, producing:

| Graph | x-axis | y-axis | Lines |
|---|---|---|---|
| 1 `graph1_response_vs_memory` | Memory (512, 1024, 1769 MB) | Mean response time (ms, log) | One per workload |
| 2 `graph2_throughput_vs_memory` | Memory | Successful throughput (req/s) | One per workload |

**RQ1 supporting table** (the proposal's secondary metrics for RQ1): per setup, `exec_mean_ms` (execution duration), `max_memory_used_mb` and `cost_per_million_usd`.

**Summary paragraph:** which workloads get faster with more memory and by how much, which don't, and what the extra memory costs.

**Done when:** both graphs have axis labels with units and a legend, and the table is complete. Graph 1 should show `cpu` and `data` getting clearly faster from 512 to 1769 MB, and `api` staying flat at about 37 ms. The table's cost should be about $20 per 1M for `cpu`, $12 for `data` and $0.2 for `api`.

---

## Member 3: RQ2, do more users at once slow it down?

**Uses:** `cpu-1024-low` (1 user), `cpu-1024` (3 users) and `cpu-1024-high` (8 users). Read `per_config.csv`.

**Build** `analysis/rq2_users.py`, producing:

| Graph | x-axis | y-axis | Lines |
|---|---|---|---|
| 3 `graph3_percentiles_vs_users` | Users (1, 3, 8) | Response time (ms) | Three: mean, p95, p99 |

**Main results table** (for the report): all 11 setups, with the round-average mean, median, standard deviation, p95 and p99 response time, successful throughput and failure rate, from `per_config.csv`.

**Summary paragraph:** do the mean, p95 and p99 response times grow with more users at once?

**Done when:** graph 3 and the table are complete with units. Round 1 reference at 1 / 3 / 8 users: mean ≈ 1,271 / 1,234 / 1,219 ms, p95 ≈ 1,336 / 1,288 / 1,264 ms, p99 ≈ 1,356 / 1,338 / 1,315 ms.

---

## Member 4: RQ3, how do the workloads compare?

**Uses:** `api-1024`, `cpu-1024` and `data-1024` (same memory and users). Read `per_config.csv`.

**Build** `analysis/rq3_workloads.py`, producing:

| Graph | Type | What |
|---|---|---|
| 4 `graph4_response_by_workload` | Bar chart | Mean response time per workload |
| 5 `graph5_throughput_by_workload` | Bar chart | Successful throughput per workload |

**RQ3 supporting table** (the proposal's execution duration metric for RQ3): per workload, `exec_mean_ms` (function working) and `overhead_ms` (network and front end, i.e. response time minus execution duration).

**Load-generator details** (promised for the midterm: "load generator location, and hardware"). Get them from whoever ran the rounds: laptop model, CPU, RAM, operating system, k6 version (`k6 version`), wired network, location (Calgary).

**Summary paragraph:** how the three workloads differ, and why. Use the supporting table: is the time mostly network or mostly computing?

**Done when:** graphs 4–5 and the table are complete with units, and the load-generator details are written up. Round 1 reference:
- mean response time ≈ 37.6 / 1,234 / 802 ms for api / cpu / data;
- throughput ≈ 79.2 / 2.43 / 3.75 req/s;
- table: `api` ≈ 1.6 ms working + 36 ms network; `cpu` ≈ 1,192 ms + 42 ms; `data` ≈ 750 ms + 52 ms.

---

## Mention in the report

- **Users were reduced** to 3 (and 1 / 3 / 8 for RQ2) instead of the proposal's 10 (and 1 / 10 / 50). The AWS account allows only 10 requests at once, and AWS rejected our request to raise it.
- **The `cpu-1024` run is used by all three research questions.**
- **Response time includes about 35–60 ms of network** from Calgary to AWS in Oregon. Execution time doesn't.
- **Cold starts during measurement are recorded, not removed** (Round 1: one, in `api-512`).

## Words you'll see

| Word | Meaning |
|---|---|
| Run | One setup tested once (150 s) |
| Round | All 11 setups once; there are 3 rounds |
| Warm-up | The first 30 s of a run, ignored |
| Cold start | The first request to a new Lambda instance; slower |
| p95 / p99 | The time that 95% / 99% of requests beat |
| Throughput | Successful requests per second |
| Little's Law | users ≈ requests per second × response time; a check that k6 itself kept up |
