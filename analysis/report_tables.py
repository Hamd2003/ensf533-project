"""Print the report's results tables as Markdown, from analysis/per_config.csv.

Run: python3 analysis/report_tables.py > /tmp/tables.md, then paste into docs/midterm-report.md.
Values are the mean of the rounds; "±" is the 95% t confidence half-width.
"""

import sys

from style import load_configs

ORDER = ("api-512", "api-1024", "api-1769", "cpu-512", "cpu-1024", "cpu-1769",
         "data-512", "data-1024", "data-1769", "cpu-1024-low", "cpu-1024-high")


def ci(row, column, digits):
    return f"{float(row[column]):,.{digits}f} ± {float(row[column + '_ci95']):,.{digits}f}"


def num(row, column, digits):
    return f"{float(row[column]):,.{digits}f}"


def main():
    configs = load_configs()
    rows = [configs[name] for name in ORDER]
    print("| Setup | MB | Users | Mean (ms) | Median (ms) | SD (ms) | p95 (ms) | p99 (ms) | Throughput (req/s) | Failed |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for row in rows:
        print(f"| {row['setup']} | {row['memory_mb']} | {row['users']} | {ci(row, 'mean_ms', 1)} | "
              f"{num(row, 'median_ms', 1)} | {num(row, 'std_ms', 1)} | {ci(row, 'p95_ms', 1)} | "
              f"{ci(row, 'p99_ms', 1)} | {ci(row, 'throughput_rps', 2)} | "
              f"{float(row['failure_rate']):.0%} |")
    print()
    print("| Setup | Execution (ms) | Overhead (ms) | Max memory used (MB) | Cost per 1M (USD) | Cold starts per run | Peak concurrency |")
    print("|---|---:|---:|---:|---:|---:|---:|")
    for row in rows:
        print(f"| {row['setup']} | {ci(row, 'exec_mean_ms', 1)} | {ci(row, 'overhead_ms', 1)} | "
              f"{num(row, 'max_memory_used_mb', 0)} | {ci(row, 'cost_per_million_usd', 2)} | "
              f"{num(row, 'cold_starts', 2)} | {num(row, 'peak_concurrency', 1)} |")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError) as error:
        print(f"Tables failed: {error}", file=sys.stderr)
        sys.exit(1)
