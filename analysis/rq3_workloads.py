"""RQ3 figure: api, cpu and data at 1024 MB and 3 users.

Reads analysis/per_config.csv. Panel (a) splits mean response time into AWS
execution and the remainder (network and front end). Error bars are 95% t
intervals across the rounds.
"""

import sys

from matplotlib.ticker import FixedLocator, FuncFormatter, NullLocator

from style import (
    GRID, INK, MUTED, ROOT, WORKLOAD, load_configs, panels, pick, polish, save, values,
)

ORDER = ("api-1024", "cpu-1024", "data-1024")
OVERHEAD = "#c9c7c1"


def breakdown(ax, rows):
    names = [row["workload"] for row in rows]
    ys = list(range(len(rows) - 1, -1, -1))
    execution = values(rows, "exec_mean_ms")
    overhead = values(rows, "overhead_ms")
    total = values(rows, "mean_ms")
    ci = values(rows, "mean_ms_ci95")
    for y, name, work, rest, whole, half in zip(ys, names, execution, overhead, total, ci):
        ax.barh(y, work, height=0.55, color=WORKLOAD[name], zorder=2,
                label="AWS execution" if name == "cpu" else None)
        ax.barh(y, rest, left=work, height=0.55, color=OVERHEAD, zorder=2,
                edgecolor="white", linewidth=1.0,
                label="network + front end" if name == "cpu" else None)
        ax.errorbar(whole, y, xerr=half, color=INK, elinewidth=0.9, capsize=2.5, zorder=3)
        share = work / whole * 100
        ax.annotate(f"{whole:,.0f} ms  ({share:.0f}% execution)", (whole + half, y),
                    textcoords="offset points", xytext=(5, 0), va="center",
                    fontsize=8, color=INK)
    ax.set_yticks(ys, names)
    ax.set_xlim(0, 1950)
    ax.tick_params(axis="y", length=0)
    ax.legend(loc="upper right", frameon=False, labelcolor=MUTED)
    polish(ax, "a", "Mean response time, split", "Time (ms)", "")
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", color=GRID, linewidth=0.6)


def throughput(ax, rows):
    names = [row["workload"] for row in rows]
    ys = list(range(len(rows) - 1, -1, -1))
    measured = values(rows, "throughput_rps")
    ci = values(rows, "throughput_rps_ci95")
    for y, name, value, half in zip(ys, names, measured, ci):
        ax.errorbar(value, y, xerr=half, color=WORKLOAD[name], marker="o", markersize=6,
                    markeredgecolor="white", markeredgewidth=0.8, elinewidth=1.0,
                    linewidth=0, zorder=3)
        ax.annotate(f"{value:,.2f}", (value, y), textcoords="offset points",
                    xytext=(0, 7), ha="center", fontsize=8, color=INK)
    ax.set_xscale("log")
    ax.xaxis.set_major_locator(FixedLocator([1, 3, 10, 30, 100]))
    ax.xaxis.set_minor_locator(NullLocator())
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _p: f"{v:,.0f}"))
    ax.set_xlim(0.8, 200)
    ax.set_ylim(-0.6, 2.6)
    ax.set_yticks(ys, names)
    ax.tick_params(axis="y", length=0)
    polish(ax, "b", "Successful throughput", "Throughput (req/s, log)", "")
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", color=GRID, linewidth=0.6)


def main():
    rows = pick(load_configs(), ORDER)
    fig, axes = panels(2, height=2.1)
    breakdown(axes[0], rows)
    throughput(axes[1], rows)
    path = save(fig, "graph3_workloads.png")
    print(f"Wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, TypeError) as error:
        print(f"Graphs failed: {error}", file=sys.stderr)
        sys.exit(1)
