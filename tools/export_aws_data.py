"""Export AWS-side measurement data for a time window (used by export-aws-data.yml).

Main output is a readable summary (job summary + summary.md): one row per run
per function. A "run" is a burst of traffic to one function; runs are split
wherever the function is idle for RUN_GAP_SECONDS. Duration statistics skip each
run's first --warmup seconds, matching the load tests' warm-up period.

Raw data for the analysis team (in the artifact):
  <out>/<function>.report.csv   one row per REPORT line (one per invocation)
  <out>/<function>.metrics.json CloudWatch metrics at 60 s resolution
  <out>/summary.md, summary.json, manifest.json

REPORT lines are read with paginated FilterLogEvents rather than Logs Insights,
which caps results at 10,000 rows.

Usage:
  python3 tools/export_aws_data.py --start 2026-10-28T15:00:00Z --end 2026-10-28T17:00:00Z \
      --functions all --label round1 --out export
"""

import argparse
import csv
import json
import math
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import boto3

ROOT = Path(__file__).resolve().parent.parent
MAX_WINDOW = timedelta(hours=24)
LOG_DELAY = timedelta(minutes=10)
PERIOD_SECONDS = 60
RUN_GAP_SECONDS = 30  # idle time that separates two runs on the same function
MAX_RUN_SECONDS = 180  # one run is 30 s warm-up + 120 s measurement; longer means runs merged

# On-demand x86 list prices (aws.amazon.com/lambda/pricing, checked 2026-10-24).
# Free tier and credits are ignored, so this is the list-price cost.
PRICE_PER_GB_SECOND = 0.0000166667
PRICE_PER_MILLION_REQUESTS = 0.20

CSV_COLUMNS = [
    "timestamp", "request_id", "duration_ms", "billed_ms", "memory_mb",
    "max_memory_used_mb", "init_duration_ms", "status", "log_stream",
]
REPORT_FIELDS = {
    "request_id": re.compile(r"RequestId: (\S+)"),
    "duration_ms": re.compile(r"\tDuration: ([\d.]+) ms"),
    "billed_ms": re.compile(r"Billed Duration: (\d+) ms"),
    "memory_mb": re.compile(r"Memory Size: (\d+) MB"),
    "max_memory_used_mb": re.compile(r"Max Memory Used: (\d+) MB"),
    "init_duration_ms": re.compile(r"Init Duration: ([\d.]+) ms"),  # cold starts only
    "status": re.compile(r"Status: (\S+)"),  # only present on timeouts/errors
}
# (metric name, statistic) pairs exported per function.
METRICS = [
    ("Invocations", "Sum"),
    ("Errors", "Sum"),
    ("Throttles", "Sum"),
    ("Duration", "Average"),
    ("Duration", "Maximum"),
    ("ConcurrentExecutions", "Maximum"),
]


def fail(message):
    print(f"::error::{message}")
    sys.exit(1)


def parse_time(value, name):
    try:
        parsed = datetime.fromisoformat(value.strip())
    except ValueError:
        fail(f"{name} is not ISO 8601 (expected e.g. 2026-10-28T15:00:00Z): {value!r}")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)  # inputs are documented as UTC
    return parsed.astimezone(timezone.utc)


def resolve_functions(value, config):
    known = [f"seng533-{w}-{m}" for w in config["workloads"] for m in config["memory_levels_mb"]]
    if value.strip().lower() == "all":
        return known
    names = [n.strip() for n in value.split(",") if n.strip()]
    unknown = [n for n in names if n not in known]
    if not names or unknown:
        fail(f"unknown function name(s) {unknown}; expected 'all' or a comma-separated subset of {known}")
    return names


def parse_report(event):
    message = event["message"]
    row = {"log_stream": event.get("logStreamName", ""), "_ms": event["timestamp"]}
    for field, pattern in REPORT_FIELDS.items():
        match = pattern.search(message)
        row[field] = match.group(1) if match else ""
    row["timestamp"] = datetime.fromtimestamp(event["timestamp"] / 1000, timezone.utc).isoformat(
        timespec="milliseconds")
    return row


def export_reports(logs, function, start, end, out_dir):
    paginator = logs.get_paginator("filter_log_events")
    pages = paginator.paginate(
        logGroupName=f"/aws/lambda/{function}",
        startTime=int(start.timestamp() * 1000),
        endTime=int(end.timestamp() * 1000),
        filterPattern='"REPORT RequestId:"',
    )
    rows = []
    try:
        for page in pages:
            rows.extend(parse_report(e) for e in page["events"])
    except logs.exceptions.ResourceNotFoundException:
        print(f"::warning::log group for {function} does not exist (never invoked?)")
    rows.sort(key=lambda r: r["_ms"])

    with open(out_dir / f"{function}.report.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return rows


def export_metrics(cloudwatch, functions, start, end, out_dir):
    queries, ids = [], {}
    for i, function in enumerate(functions):
        for j, (metric, stat) in enumerate(METRICS):
            query_id = f"m{i}_{j}"
            ids[query_id] = (function, f"{metric}_{stat}")
            queries.append({
                "Id": query_id,
                "MetricStat": {
                    "Metric": {
                        "Namespace": "AWS/Lambda",
                        "MetricName": metric,
                        "Dimensions": [{"Name": "FunctionName", "Value": function}],
                    },
                    "Period": PERIOD_SECONDS,
                    "Stat": stat,
                },
                "ReturnData": True,
            })

    series = {f: {} for f in functions}
    paginator = cloudwatch.get_paginator("get_metric_data")
    for page in paginator.paginate(MetricDataQueries=queries, StartTime=start, EndTime=end,
                                   ScanBy="TimestampAscending"):
        for result in page["MetricDataResults"]:
            function, key = ids[result["Id"]]
            entry = series[function].setdefault(key, {"timestamps": [], "values": []})
            entry["timestamps"].extend(t.astimezone(timezone.utc).isoformat() for t in result["Timestamps"])
            entry["values"].extend(result["Values"])

    for function in functions:
        with open(out_dir / f"{function}.metrics.json", "w") as f:
            json.dump({
                "function": function,
                "start": start.isoformat(),
                "end": end.isoformat(),
                "period_seconds": PERIOD_SECONDS,
                "metrics": series[function],
            }, f, indent=2)
    return series


def split_runs(rows):
    """Group a function's invocations into runs separated by idle gaps."""
    runs = []
    for row in rows:
        if runs and row["_ms"] - runs[-1][-1]["_ms"] < RUN_GAP_SECONDS * 1000:
            runs[-1].append(row)
        else:
            runs.append([row])
    return runs


def percentile(sorted_values, p):
    """Linear interpolation between closest ranks (same as numpy's default)."""
    k = (len(sorted_values) - 1) * p / 100
    lo = math.floor(k)
    hi = min(lo + 1, len(sorted_values) - 1)
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * (k - lo)


def metric_in_run(metrics, key, run_start_ms, run_end_ms, combine):
    """Combine the 60 s metric points that overlap the run (e.g. sum or max)."""
    entry = metrics.get(key, {"timestamps": [], "values": []})
    values = [
        v for t, v in zip(entry["timestamps"], entry["values"])
        if (ms := datetime.fromisoformat(t).timestamp() * 1000) <= run_end_ms
        and ms + PERIOD_SECONDS * 1000 > run_start_ms
    ]
    return combine(values) if values else None


def summarize_run(function, run, warmup_s, metrics):
    start_ms, end_ms = run[0]["_ms"], run[-1]["_ms"]
    measured = [r for r in run if r["_ms"] >= start_ms + warmup_s * 1000]
    short_run = not measured  # shorter than the warm-up: use every request instead
    if short_run:
        measured = run

    durations = sorted(float(r["duration_ms"]) for r in measured)
    billed = [int(r["billed_ms"]) for r in measured]
    memory_mb = int(run[0]["memory_mb"])
    inits = [float(r["init_duration_ms"]) for r in run if r["init_duration_ms"]]
    mean_billed = sum(billed) / len(billed)
    cost_per_million = (mean_billed / 1000 * memory_mb / 1024 * PRICE_PER_GB_SECOND * 1_000_000
                        + PRICE_PER_MILLION_REQUESTS)

    return {
        "function": function,
        "run_start": datetime.fromtimestamp(start_ms / 1000, timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "run_end": datetime.fromtimestamp(end_ms / 1000, timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "length_s": round((end_ms - start_ms) / 1000),
        "requests_total": len(run),
        "requests_measured": len(measured),
        "short_run": short_run,
        "duration_mean_ms": round(sum(durations) / len(durations), 1),
        "duration_p50_ms": round(percentile(durations, 50), 1),
        "duration_p95_ms": round(percentile(durations, 95), 1),
        "duration_p99_ms": round(percentile(durations, 99), 1),
        "duration_max_ms": round(durations[-1], 1),
        "billed_mean_ms": round(mean_billed, 1),
        "cold_starts": len(inits),
        "init_mean_ms": round(sum(inits) / len(inits), 1) if inits else None,
        "environments": len({r["log_stream"] for r in run}),
        "max_memory_used_mb": max(int(r["max_memory_used_mb"]) for r in run),
        "memory_mb": memory_mb,
        "errors_or_timeouts": sum(1 for r in run if r["status"]),
        "throttles": metric_in_run(metrics, "Throttles_Sum", start_ms, end_ms, sum),
        "peak_concurrency": metric_in_run(metrics, "ConcurrentExecutions_Maximum", start_ms, end_ms, max),
        "cost_per_million_usd": round(cost_per_million, 2),
    }


def fmt(value):
    if value is None:
        return "–"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def render_summary(label, start, end, warmup_s, runs, missing):
    lines = [
        f"## AWS-side results `{label}`",
        "",
        f"Window **{start:%Y-%m-%d %H:%M:%S}** to **{end:%Y-%m-%d %H:%M:%S}** UTC. "
        f"One row per run. A new run starts after {RUN_GAP_SECONDS} s with no requests. "
        f"Duration figures skip each run's first **{warmup_s} s** (warm-up).",
        "",
    ]
    if not runs:
        lines += ["No invocations in this window. Check the times (UTC) and wait 10 minutes after the last run.", ""]
    else:
        lines += [
            "### Execution duration (ms, warm-up excluded)",
            "",
            "| Function | Run start (UTC) | Length (s) | Requests measured | Mean | p50 | p95 | p99 | Max |",
            "|---|---|--:|--:|--:|--:|--:|--:|--:|",
        ]
        for r in runs:
            measured = f"{r['requests_measured']}{' †' if r['short_run'] else ''}"
            length = f"{r['length_s']}{' ⚠️' if r['length_s'] > MAX_RUN_SECONDS else ''}"
            lines.append(
                f"| `{r['function']}` | {r['run_start']} | {length} | {measured} | "
                f"{fmt(r['duration_mean_ms'])} | {fmt(r['duration_p50_ms'])} | {fmt(r['duration_p95_ms'])} | "
                f"{fmt(r['duration_p99_ms'])} | {fmt(r['duration_max_ms'])} |")
        lines += [
            "",
            "### Cold starts, capacity and cost (whole run)",
            "",
            "| Function | Run start (UTC) | Requests | Cold starts | Init mean (ms) | Environments | "
            "Peak concurrency | Throttles | Errors / timeouts | Max memory used (MB) | Billed mean (ms) | Cost per 1M req (USD) |",
            "|---|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|",
        ]
        for r in runs:
            lines.append(
                f"| `{r['function']}` | {r['run_start']} | {r['requests_total']} | {r['cold_starts']} | "
                f"{fmt(r['init_mean_ms'])} | {r['environments']} | {fmt(r['peak_concurrency'])} | "
                f"{fmt(r['throttles'])} | {r['errors_or_timeouts']} | "
                f"{r['max_memory_used_mb']} / {r['memory_mb']} | {fmt(r['billed_mean_ms'])} | "
                f"{r['cost_per_million_usd']:.2f} |")
    if missing:
        lines += ["", "No invocations in the window for: " + ", ".join(f"`{f}`" for f in missing)]
    lines += [
        "",
        "<details><summary>What the columns mean</summary>",
        "",
        "- **Execution duration**: time Lambda spent running the handler (REPORT `Duration`), "
        "excluding network and Function URL overhead. Client-side response time and throughput come from k6, not from here.",
        "- **† Short run**: shorter than the warm-up, so every request is included.",
        f"- **⚠️ Long run**: over {MAX_RUN_SECONDS} s, so two runs on the same function were probably less than "
        f"{RUN_GAP_SECONDS} s apart and got merged. Export each of them with its own start/end window.",
        "- **Cold starts**: requests with an `Init Duration`, meaning a new execution environment was created. "
        "**Environments**: distinct log streams (one per environment).",
        "- **Peak concurrency / Throttles**: CloudWatch 1-minute `ConcurrentExecutions` (max) and `Throttles` (sum) "
        "for the minutes overlapping the run. Throttles are requests rejected with HTTP 429.",
        "- **Cost per 1M requests**: mean billed duration x memory x "
        f"${PRICE_PER_GB_SECOND}/GB-s + ${PRICE_PER_MILLION_REQUESTS:.2f}/1M requests (x86 on-demand list price, "
        "no free tier). It uses requests after the warm-up; billed duration includes init time on cold starts.",
        "- Raw per-request data (CSV) and 1-minute metrics are in the run's artifact.",
        "",
        "</details>",
        "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--start", required=True, help="ISO 8601, UTC")
    parser.add_argument("--end", required=True, help="ISO 8601, UTC")
    parser.add_argument("--functions", default="all", help="'all' or comma-separated function names")
    parser.add_argument("--label", required=True, help="e.g. round1")
    parser.add_argument("--warmup", type=int, default=30, help="seconds skipped at the start of each run")
    parser.add_argument("--out", default="export", help="output directory")
    args = parser.parse_args()

    config = json.loads((ROOT / "config" / "experiment.json").read_text())
    start, end = parse_time(args.start, "start"), parse_time(args.end, "end")
    if end <= start:
        fail("end must be after start")
    if end - start > MAX_WINDOW:
        fail("window must be at most 24 hours; export longer periods in several runs")
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", args.label):
        fail("label may only contain letters, digits, '.', '_' and '-'")
    if not 0 <= args.warmup <= 600:
        fail("warmup must be between 0 and 600 seconds")
    if end > datetime.now(timezone.utc) - LOG_DELAY:
        print("::warning::end is less than 10 minutes ago; the most recent log lines may be missing")
    functions = resolve_functions(args.functions, config)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    region = config["region"]
    logs = boto3.client("logs", region_name=region)
    cloudwatch = boto3.client("cloudwatch", region_name=region)

    rows_by_function = {fn: export_reports(logs, fn, start, end, out_dir) for fn in functions}
    metrics = export_metrics(cloudwatch, functions, start, end, out_dir)

    runs = [
        summarize_run(fn, run, args.warmup, metrics[fn])
        for fn, rows in rows_by_function.items()
        for run in split_runs(rows)
    ]
    runs.sort(key=lambda r: (r["run_start"], r["function"]))
    missing = [fn for fn, rows in rows_by_function.items() if not rows]

    summary = render_summary(args.label, start, end, args.warmup, runs, missing)
    (out_dir / "summary.md").write_text(summary)
    with open(out_dir / "summary.json", "w") as f:
        json.dump({"label": args.label, "warmup_s": args.warmup, "run_gap_s": RUN_GAP_SECONDS, "runs": runs}, f, indent=2)
    with open(out_dir / "manifest.json", "w") as f:
        json.dump({
            "label": args.label,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "region": region,
            "warmup_s": args.warmup,
            "exported_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "functions": {fn: {"report_lines": len(rows)} for fn, rows in rows_by_function.items()},
        }, f, indent=2)

    print(summary)
    if path := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(path, "a") as f:
            f.write(summary)


if __name__ == "__main__":
    main()
