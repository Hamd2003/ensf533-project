"""Build Member 1's shared tables: python3 analysis/build_tables.py."""

import csv
import json
import math
import statistics
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MEASURE_SECONDS = 120
PER_RUN_COLUMNS = [
    "round", "setup", "workload", "memory_mb", "users", "requests",
    "mean_ms", "median_ms", "std_ms", "p95_ms", "p99_ms", "successful",
    "throughput_rps", "failure_rate", "throttled", "function_errors", "timeouts",
    "wrong_answers", "exec_mean_ms", "overhead_ms", "billed_mean_ms",
    "cost_per_million_usd", "max_memory_used_mb", "cold_starts",
    "peak_concurrency", "littles_law",
]
CONFIG_METRICS = [
    "mean_ms", "median_ms", "std_ms", "p95_ms", "p99_ms", "throughput_rps",
    "failure_rate", "exec_mean_ms", "overhead_ms", "max_memory_used_mb",
    "cost_per_million_usd", "cold_starts", "peak_concurrency",
]
CONFIG_COLUMNS = ["setup", "workload", "memory_mb", "users", *CONFIG_METRICS]
CHECK_COLUMNS = [
    "round", "setup", "users", "littles_law", "deviation_pct", "requests",
    "failed", "throttled", "function_errors", "timeouts", "wrong_answers",
    "other_failures", "cold_starts", "flag", "reason",
]


def percentile(values, fraction):
    """Linear interpolation between sorted observations (rank = (n - 1) * p)."""
    rank = (len(values) - 1) * fraction
    low, high = math.floor(rank), math.ceil(rank)
    return values[low] + (values[high] - values[low]) * (rank - low)


def nonnegative(value):
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"Expected a finite, nonnegative number, got {value!r}")
    return number


def peak_concurrency(metrics, requests):
    # Include 60 s buckets overlapping measured sends through final completion.
    start = min(r["t"] for r in requests)
    end = max(r["t"] + r["duration_ms"] for r in requests)
    series = metrics["metrics"]["ConcurrentExecutions_Maximum"]
    period_ms = metrics["period_seconds"] * 1000
    if period_ms != 60000 or len(series["timestamps"]) != len(series["values"]):
        raise ValueError("Expected aligned, 60-second concurrency metrics")
    values = [
        nonnegative(value)
        for timestamp, value in zip(series["timestamps"], series["values"])
        if (ms := datetime.fromisoformat(timestamp).timestamp() * 1000) <= end
        and ms + period_ms > start
    ]
    if not values:
        raise ValueError("No concurrency metrics overlap the measured run")
    return max(values)


def summarize_run(round_number, setup, users, requests, aws, metrics):
    workload, memory, *_ = setup.split("-")
    memory = int(memory)
    joined = []
    for request in requests:
        report = aws[request["request_id"]]
        if int(report["memory_mb"]) != memory:
            raise ValueError(f"AWS memory does not match {setup}")
        joined.append(report)
    durations = sorted(nonnegative(r["duration_ms"]) for r in requests)
    successful = sum(r["valid"] is True for r in requests)
    throttled = function_errors = timeouts = wrong_answers = 0
    for request, report in zip(requests, joined):
        status = request["status"]
        throttled += status == 429
        function_errors += 500 <= status <= 599 and report["status"] != "timeout"
        timeouts += status == 0 or (500 <= status <= 599 and report["status"] == "timeout")
        wrong_answers += status == 200 and request["valid"] is False
    mean_ms = statistics.mean(durations)
    exec_mean = statistics.mean(nonnegative(r["duration_ms"]) for r in joined)
    billed_mean = statistics.mean(nonnegative(r["billed_ms"]) for r in joined)
    return {
        "round": round_number, "setup": setup, "workload": workload,
        "memory_mb": memory, "users": users, "requests": len(requests),
        "mean_ms": mean_ms, "median_ms": statistics.median(durations),
        "std_ms": statistics.stdev(durations) if len(durations) > 1 else 0.0,
        "p95_ms": percentile(durations, 0.95), "p99_ms": percentile(durations, 0.99),
        "successful": successful, "throughput_rps": successful / MEASURE_SECONDS,
        "failure_rate": 1 - successful / len(requests),
        "throttled": throttled, "function_errors": function_errors,
        "timeouts": timeouts, "wrong_answers": wrong_answers,
        "exec_mean_ms": exec_mean, "overhead_ms": mean_ms - exec_mean,
        "billed_mean_ms": billed_mean,
        "cost_per_million_usd":
            billed_mean / 1000 * memory / 1024 * 0.0000166667 * 1_000_000 + 0.20,
        "max_memory_used_mb": max(nonnegative(r["max_memory_used_mb"]) for r in joined),
        "cold_starts": sum(r["cold"] is True for r in requests),
        "peak_concurrency": peak_concurrency(metrics, requests),
        "littles_law": len(requests) / MEASURE_SECONDS * mean_ms / 1000,
    }


def build_runs(root):
    config = json.loads((root / "config/experiment.json").read_text())
    setups = {
        f"{workload}-{memory}": 3
        for workload in config["workloads"] for memory in config["memory_levels_mb"]
    }
    setups.update({"cpu-1024-low": 1, "cpu-1024-high": 8})
    rounds = sorted(
        (p for p in (root / "results").glob("round*") if p.is_dir() and p.name[5:].isdigit()),
        key=lambda p: int(p.name[5:]),
    )
    if not rounds:
        raise ValueError("No results/round<N>/ folders found")
    rows, seen_requests = [], set()
    for folder in rounds:
        round_number = int(folder.name[5:])
        paths = list((folder / "k6-measured-data").glob("*.jsonl"))
        expected = {f"restricted-r{round_number}-{setup}.jsonl" for setup in setups}
        if {p.name for p in paths} != expected:
            raise ValueError(f"{folder}: expected exactly one JSONL for each of the 11 setups")
        aws_by_function, metrics_by_function = {}, {}
        for setup in setups:
            function = "-".join(setup.split("-")[:2])
            if function in aws_by_function:
                continue
            prefix = folder / "aws-export-data" / f"seng533-{function}"
            with prefix.with_suffix(".report.csv").open(newline="") as stream:
                reports = list(csv.DictReader(stream))
            aws = {r["request_id"]: r for r in reports}
            if "" in aws or len(aws) != len(reports):
                raise ValueError(f"{prefix}: missing or duplicate AWS request_id")
            aws_by_function[function] = aws
            metrics_by_function[function] = json.loads(prefix.with_suffix(".metrics.json").read_text())
        for setup, users in setups.items():
            path = folder / "k6-measured-data" / f"restricted-r{round_number}-{setup}.jsonl"
            requests = []
            for line_number, line in enumerate(path.read_text().splitlines(), 1):
                request = json.loads(line)
                if request["phase"] == "warmup":
                    continue
                if (request["phase"] != "measure" or request["setup"] != setup
                        or request["vus"] != users or request["profile"] != "restricted"
                        or type(request["valid"]) is not bool
                        or type(request["status"]) is not int
                        or (request["valid"] and request["status"] != 200)):
                    raise ValueError(f"{path}:{line_number}: inconsistent request metadata")
                request_id = request["request_id"]
                if not request_id or request_id in seen_requests:
                    raise ValueError(f"{path}:{line_number}: missing or duplicate measured request_id")
                seen_requests.add(request_id)
                nonnegative(request["t"])
                nonnegative(request["duration_ms"])
                requests.append(request)
            if not requests:
                raise ValueError(f"{path}: no measured requests")
            function = "-".join(setup.split("-")[:2])
            aws = aws_by_function[function]
            missing = [r["request_id"] for r in requests if r["request_id"] not in aws]
            if missing:
                raise ValueError(f"{path}: {len(missing)} measured requests have no AWS record")
            rows.append(summarize_run(round_number, setup, users, requests, aws,
                                      metrics_by_function[function]))
    return rows


def average_configs(runs):
    rows = []
    for setup in dict.fromkeys(r["setup"] for r in runs):
        group = [r for r in runs if r["setup"] == setup]
        row = {key: group[0][key] for key in CONFIG_COLUMNS[:4]}
        row.update({key: statistics.mean(r[key] for r in group) for key in CONFIG_METRICS})
        rows.append(row)
    return rows


def check_runs(runs):
    checks = []
    for run in runs:
        deviation = abs(run["littles_law"] - run["users"]) / run["users"] * 100
        failed = run["requests"] - run["successful"]
        reasons = []
        if deviation > 10:
            reasons.append("Little's law differs from users by more than 10%")
        if failed:
            reasons.append(f"{failed} failed requests")
        row = {key: run[key] for key in CHECK_COLUMNS if key in run}
        row.update(deviation_pct=deviation, failed=failed,
                   other_failures=failed - sum(run[key] for key in
                       ("throttled", "function_errors", "timeouts", "wrong_answers")),
                   flag=bool(reasons), reason="; ".join(reasons))
        checks.append(row)
    return checks


def write_csv(path, columns, rows):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def render_checks(checks):
    flagged = [r for r in checks if r["flag"]]
    lines = [
        "# Member 1: data and checks", "",
        "Rebuild from the repository root: `python3 analysis/build_tables.py`.", "",
        f"Processed {len(checks)} runs across {len({r['round'] for r in checks})} rounds; "
        f"{sum(r['requests'] for r in checks):,} measured requests. "
        f"**{len(flagged)} runs flagged for repo-owner review.**", "",
        "## Checks table", "",
        "Little's law estimates users as requests / 120 × mean response time / 1000. "
        "Deviation is the absolute percentage difference from configured users. "
        "Flag a run if deviation exceeds 10% or any request fails.", "",
        "| Round | Setup | Users | Little's law | Deviation (%) | Failed | Throttled | Function errors | Timeouts | Wrong answers | Other failures | Cold starts | Result |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in checks:
        lines.append(
            f"| {row['round']} | {row['setup']} | {row['users']} | {row['littles_law']:.3f} | "
            f"{row['deviation_pct']:.2f} | {row['failed']} | {row['throttled']} | "
            f"{row['function_errors']} | {row['timeouts']} | {row['wrong_answers']} | "
            f"{row['other_failures']} | {row['cold_starts']} | {'REVIEW' if row['flag'] else 'PASS'} |")
    if flagged:
        lines += ["", "## Runs requiring review", ""]
        lines += [f"- Round {r['round']}, `{r['setup']}`: {r['reason']}." for r in flagged]
    lines += [
        "", "## Calculation notes", "",
        "- Only `phase == \"measure\"` requests enter the calculations. AWS records are joined "
        "by `request_id` within the corresponding round and function. Missing or duplicate "
        "required records stop the build before any output is written.",
        "- Response statistics include all measured requests. Success means `valid == true`; "
        "successful throughput divides that count by exactly 120 seconds. Failure rate is a fraction.",
        "- `std_ms` is sample standard deviation (denominator n − 1; zero for one request). "
        "p95 and p99 use linear interpolation at rank (n − 1) × percentile.",
        "- `per_config.csv` is the unweighted arithmetic mean of each run's metrics. "
        "Requests from separate runs are never pooled. Counts such as cold starts and "
        "per-run maxima can therefore have fractional averages. CSV values retain full precision.",
        "- AWS execution, billing and maximum memory use come only from matched measured "
        "requests. Overhead is mean response time minus mean AWS execution time. Cost uses "
        "the guide's USD formula, including $0.20 per million requests.",
        "- Peak concurrency uses 60-second AWS buckets overlapping the interval from the "
        "first measured request send to the last measured response completion. It is a "
        "minute-level function metric, so a bucket can include activity outside that interval. "
        "Observed peaks are retained even when they exceed configured users.",
        "- Cold starts count measured k6 requests with `cold == true`. Cold starts alone "
        "do not flag a run. `other_failures` preserves failures outside the guide's four named types.",
        "", "## Handoff", "",
        "Members 2–4 should read `analysis/per_config.csv` for round-average results and "
        "`analysis/per_run.csv` for individual runs. Use the checks table above in the midterm report.",
    ]
    return "\n".join(lines) + "\n"


def main():
    runs = build_runs(ROOT)
    configs = average_configs(runs)
    checks = check_runs(runs)
    output = ROOT / "analysis"
    output.mkdir(exist_ok=True)
    write_csv(output / "per_run.csv", PER_RUN_COLUMNS, runs)
    write_csv(output / "per_config.csv", CONFIG_COLUMNS, configs)
    write_csv(output / "checks.csv", CHECK_COLUMNS, checks)
    (output / "checks.md").write_text(render_checks(checks))
    print(f"Built {len(runs)} run rows, {len(configs)} setup rows, "
          f"and {len(checks)} checks; {sum(r['flag'] for r in checks)} flagged runs.")
    for row in checks:
        if row["flag"]:
            print(f"REVIEW round {row['round']} {row['setup']}: {row['reason']}")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, TypeError) as error:
        print(f"Build failed: {error}", file=sys.stderr)
        sys.exit(1)
