"""Export AWS-side measurement data for a time window (used by export-aws-data.yml).

For each function:
  <out>/<function>.report.csv   one row per REPORT line (one per invocation)
  <out>/<function>.metrics.json CloudWatch metrics at 60 s resolution

REPORT lines are read with paginated FilterLogEvents rather than Logs Insights,
which caps results at 10,000 rows.

Usage:
  python3 tools/export_aws_data.py --start 2026-10-28T15:00:00Z --end 2026-10-28T17:00:00Z \
      --functions all --label round1 --out export
"""

import argparse
import csv
import json
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
    row = {"log_stream": event.get("logStreamName", "")}
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
    rows.sort(key=lambda r: r["timestamp"])

    with open(out_dir / f"{function}.report.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
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


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--start", required=True, help="ISO 8601, UTC")
    parser.add_argument("--end", required=True, help="ISO 8601, UTC")
    parser.add_argument("--functions", default="all", help="'all' or comma-separated function names")
    parser.add_argument("--label", required=True, help="e.g. round1")
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
    if end > datetime.now(timezone.utc) - LOG_DELAY:
        print("::warning::end is less than 10 minutes ago; the most recent log lines may be missing")
    functions = resolve_functions(args.functions, config)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    region = config["region"]
    logs = boto3.client("logs", region_name=region)
    cloudwatch = boto3.client("cloudwatch", region_name=region)

    counts = {}
    for function in functions:
        rows = export_reports(logs, function, start, end, out_dir)
        counts[function] = (len(rows), sum(1 for r in rows if r["init_duration_ms"]))
        print(f"{function}: {counts[function][0]} REPORT lines, {counts[function][1]} cold starts")
    export_metrics(cloudwatch, functions, start, end, out_dir)

    with open(out_dir / "manifest.json", "w") as f:
        json.dump({
            "label": args.label,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "region": region,
            "exported_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "functions": {fn: {"report_lines": n, "cold_starts": c} for fn, (n, c) in counts.items()},
        }, f, indent=2)

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as f:
            f.write(f"### AWS data export `{args.label}`\n\n{start.isoformat()} to {end.isoformat()}\n\n"
                    "| Function | REPORT lines | Cold starts |\n|---|---|---|\n")
            f.writelines(f"| `{fn}` | {n} | {c} |\n" for fn, (n, c) in counts.items())


if __name__ == "__main__":
    main()
