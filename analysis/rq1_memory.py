"""RQ1 figure: response time, throughput and cost against memory, at 3 users.

Reads analysis/per_config.csv. Error bars are 95% t intervals across the rounds.
The dashed lines show ideal CPU scaling: time proportional to 512 / memory.
"""

import sys

from matplotlib.ticker import FixedLocator, FuncFormatter, NullLocator

from style import (
    INK, MUTED, ROOT, WORKLOAD, errorbar, load_configs, panels, pick, polish,
    save, values,
)

WORKLOADS = ("api", "cpu", "data")
MEMORY = (512, 1024, 1769)


def log_axes(ax, yticks):
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.xaxis.set_major_locator(FixedLocator(MEMORY))
    ax.xaxis.set_minor_locator(NullLocator())
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _p: f"{v:,.0f}"))
    ax.yaxis.set_major_locator(FixedLocator(yticks))
    ax.yaxis.set_minor_locator(NullLocator())
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _p: f"{v:,.4g}"))
    ax.set_xlim(440, 2100)


def draw(configs):
    fig, axes = panels(3, height=2.6)
    columns = (
        ("mean_ms", "Mean response time", "Response time (ms, log)", [30, 100, 300, 1000, 3000]),
        ("throughput_rps", "Successful throughput", "Throughput (req/s, log)", [1, 3, 10, 30, 100]),
        ("cost_per_million_usd", "Cost per million requests", "USD (log)", [0.1, 0.3, 1, 3, 10, 30]),
    )
    for ax, letter, (column, title, ylabel, yticks) in zip(axes, "abc", columns):
        for name in WORKLOADS:
            rows = pick(configs, [f"{name}-{mb}" for mb in MEMORY])
            ys = values(rows, column)
            errorbar(ax, MEMORY, ys, values(rows, f"{column}_ci95"), WORKLOAD[name],
                     label=name)
            if column == "mean_ms" and name != "api":
                ideal = [ys[0] * 512 / mb for mb in MEMORY]
                ax.plot(MEMORY, ideal, color=INK, linestyle=(0, (2, 2)),
                        linewidth=0.8, zorder=4,
                        label="ideal: time × memory constant" if name == "cpu" else None)
        log_axes(ax, yticks)
        polish(ax, letter, title, "Memory (MB, log)", ylabel)
    axes[0].set_ylim(22, 4000)
    axes[1].set_ylim(0.8, 160)
    axes[2].set_ylim(0.1, 40)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="outside lower center", ncol=4, frameon=False,
               labelcolor=MUTED)
    return save(fig, "graph1_memory.png")


def main():
    path = draw(load_configs())
    print(f"Wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, TypeError) as error:
        print(f"Graphs failed: {error}", file=sys.stderr)
        sys.exit(1)
