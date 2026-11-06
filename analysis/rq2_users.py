"""RQ2 figure: cpu workload at 1024 MB with 1, 3 and 8 users at once.

Reads analysis/per_config.csv and analysis/per_run.csv. Error bars are 95% t
intervals across the three rounds.
"""

import sys

from style import (
    BLUE, INK, MUTED, NEUTRAL, ORANGE, ROOT, AQUA, errorbar, load_configs, load_runs,
    panels, pick, polish, save, values,
)

SETUPS = ("cpu-1024-low", "cpu-1024", "cpu-1024-high")
USERS = (1, 3, 8)
SERIES = (("mean_ms", "mean", BLUE), ("p95_ms", "p95", ORANGE), ("p99_ms", "p99", AQUA))
GRID_BAR = "#dcdad4"
SHIFT = {"mean_ms": -0.18, "p95_ms": 0.0, "p99_ms": 0.18}


def users_axis(ax):
    ax.set_xticks(USERS)
    ax.set_xlim(0, 9)


def percentiles(ax, rows):
    for column, label, color in SERIES:
        xs = [users + SHIFT[column] for users in USERS]
        errorbar(ax, xs, values(rows, column), values(rows, f"{column}_ci95"), color,
                 label=label)
    users_axis(ax)
    ax.set_ylim(800, 1600)
    ax.legend(loc="lower right", ncol=3, frameon=False, labelcolor=MUTED,
              handletextpad=0.3, columnspacing=0.8)
    polish(ax, "a", "Mean, p95, p99 (95% CI)", "Users at once", "Response time (ms)")


def rounds(ax, runs):
    for users in USERS:
        means = [float(r["mean_ms"]) for r in runs
                 if r["setup"] in SETUPS and int(r["users"]) == users]
        if len(means) != 3:
            raise ValueError(f"Expected 3 rounds at {users} users, found {len(means)}")
        ax.plot([users, users], [min(means), max(means)], color=GRID_BAR, linewidth=6,
                solid_capstyle="round", zorder=1)
        ax.scatter([users] * 3, means, s=16, color=BLUE, edgecolor="white",
                   linewidth=0.6, zorder=3)
        ax.annotate(f"{max(means) - min(means):.0f} ms", (users, max(means)),
                    textcoords="offset points", xytext=(0, 6), ha="center",
                    fontsize=8, color=MUTED)
    users_axis(ax)
    ax.set_ylim(1100, 1300)
    polish(ax, "b", "Mean of each round (range)", "Users at once (= environments)", "Mean response time (ms)")


def throughput(ax, rows):
    measured = values(rows, "throughput_rps")
    predicted = [users / (r / 1000) for users, r in zip(USERS, values(rows, "mean_ms"))]
    ax.plot(USERS, predicted, color=NEUTRAL, linestyle=(0, (3, 2)), linewidth=0.9,
            zorder=2, label="N / R (law)")
    errorbar(ax, USERS, measured, values(rows, "throughput_rps_ci95"), BLUE,
             label="measured", line=False)
    for users, value in zip(USERS, measured):
        ax.annotate(f"{value:.2f}", (users, value), textcoords="offset points",
                    xytext=(-6, 5), ha="right", fontsize=8, color=INK)
    users_axis(ax)
    ax.set_ylim(0, 8)
    ax.legend(loc="upper left", frameon=False, labelcolor=MUTED)
    polish(ax, "c", "Successful throughput", "Users at once", "Throughput (req/s)")


def main():
    rows = pick(load_configs(), SETUPS)
    runs = load_runs()
    fig, axes = panels(3, height=2.5)
    percentiles(axes[0], rows)
    rounds(axes[1], runs)
    throughput(axes[2], rows)
    path = save(fig, "graph2_users.png")
    print(f"Wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, TypeError) as error:
        print(f"Graph failed: {error}", file=sys.stderr)
        sys.exit(1)
