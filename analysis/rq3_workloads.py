
import csv
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

ROOT = Path(__file__).resolve().parent
SETUPS = ("api-1024", "cpu-1024", "data-1024")
METRICS = ("mean_ms", "throughput_rps", "exec_mean_ms", "overhead_ms")
COLORS = ("#0072B2", "#D55E00", "#009E73")


def load_rows():
    with (ROOT / "per_config.csv").open(newline="") as stream:
        configs = list(csv.DictReader(stream))
    with (ROOT / "per_run.csv").open(newline="") as stream:
        runs = list(csv.DictReader(stream))
    selected = []
    for setup in SETUPS:
        matches = [r for r in configs if r["setup"] == setup]
        if len(matches) != 1:
            raise ValueError(f"Expected exactly one configuration for {setup}")
        row = matches[0]
        group = [r for r in runs if r["setup"] == setup]
        if len(group) != 3 or {r["round"] for r in group} != {"1", "2", "3"}:
            raise ValueError(f"Expected one run in each of three rounds for {setup}")
        for record in [row, *group]:
            if (record["memory_mb"] != "1024" or record["users"] != "3"
                    or record["workload"] != setup.split("-")[0]):
                raise ValueError(f"Inconsistent controlled comparison: {setup}")
            for metric in METRICS:
                value = float(record[metric])
                if not math.isfinite(value) or value < 0:
                    raise ValueError(f"Invalid {metric} for {setup}")
        for metric in METRICS:
            expected = sum(float(r[metric]) for r in group) / 3
            if not math.isclose(float(row[metric]), expected, rel_tol=1e-10, abs_tol=1e-9):
                raise ValueError(f"Round average does not match: {setup}, {metric}")
        if not math.isclose(float(row["mean_ms"]),
                            float(row["exec_mean_ms"]) + float(row["overhead_ms"]),
                            abs_tol=1e-9):
            raise ValueError(f"Execution plus overhead does not match: {setup}")
        selected.append(row)
    return selected, [r for r in runs if r["setup"] in SETUPS]


def plot(rows, metric, filename, title, ylabel, logarithmic=False):
    plt.rcParams.update({"font.family": "sans-serif", "font.size": 11})
    fig, ax = plt.subplots(figsize=(7.4, 4.8), layout="constrained")
    values = [float(r[metric]) for r in rows]
    bars = ax.bar([r["workload"].upper() for r in rows], values,
                  color=COLORS, width=0.56, zorder=3)
    ax.set_title(title + "\n1024 MB · 3 users · mean of three rounds", loc="left", pad=16)
    ax.set_xlabel("Workload")
    ax.set_ylabel(ylabel)
    if logarithmic:
        ax.set_yscale("log")
        ax.set_ylim(1, max(values) * 2.8)
        ax.set_yticks([1, 10, 100, 1000])
    else:
        ax.set_ylim(0, max(values) * 1.22)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    for bar, value in zip(bars, values):
        ax.annotate(f"{value:,.2f}", (bar.get_x() + bar.get_width()/2, value),
                    xytext=(0, 7), textcoords="offset points", ha="center", fontsize=11)
    ax.grid(axis="y", which="major", color="#dddddd", zorder=0)
    ax.spines[["top", "right"]].set_visible(False)
    note = "30 s warm-up excluded; 120 s measurement per round."
    if logarithmic:
        note += " Logarithmic y-axis; baseline = 1 ms."
    fig.text(0.01, -0.015, note, fontsize=9, color="#444444")
    fig.savefig(ROOT / "figures" / filename, dpi=200, bbox_inches="tight",
                metadata={"Software": "RQ3 workload analysis"})
    plt.close(fig)


def write_table(filename, fields, rows):
    with (ROOT / filename).open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore",
                                lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main():
    rows, runs = load_rows() 
    (ROOT / "figures").mkdir(exist_ok=True)
    plot(rows, "mean_ms", "graph4_response_by_workload.png",
         "Graph 4: Mean response time by workload", "Mean response time (ms, log scale)", True)
    plot(rows, "throughput_rps", "graph5_throughput_by_workload.png",
         "Graph 5: Successful throughput by workload", "Successful throughput (requests/s)")
    write_table("rq3_supporting_table.csv",
                ["setup", "workload", "memory_mb", "users", *METRICS, "failure_rate"], rows)
    write_table("rq3_per_round.csv",
                ["round", "setup", "requests", *METRICS, "failure_rate", "cold_starts"], runs)
    print("Validated nine RQ3 runs; wrote graphs 4–5 and two RQ3 tables.")


if __name__ == "__main__":
    main()
