"""Graph 3 for RQ2: response time against users at once.

Reads analysis/per_config.csv and writes
analysis/figures/graph3_percentiles_vs_users.png.
"""

import csv
import sys
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "analysis" / "per_config.csv"
FIGURE = ROOT / "analysis" / "figures" / "graph3_percentiles_vs_users.png"

# cpu at 1024 MB. Ordered by users: 1, 3, 8.
SETUPS = ("cpu-1024-low", "cpu-1024", "cpu-1024-high")
SERIES = (
    ("mean_ms", "Mean", "#0072B2", "o"),
    ("p95_ms", "p95", "#E69F00", "s"),
    ("p99_ms", "p99", "#D55E00", "D"),
)


def load_rows():
    with CONFIG.open(newline="") as stream:
        by_setup = {row["setup"]: row for row in csv.DictReader(stream)}
    missing = [name for name in SETUPS if name not in by_setup]
    if missing:
        raise ValueError(f"per_config.csv is missing {missing}")
    rows = [by_setup[name] for name in SETUPS]
    rows.sort(key=lambda row: int(row["users"]))
    return rows


def plot(rows):
    users = [int(row["users"]) for row in rows]
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.size": 11,
        "axes.linewidth": 0.8,
        "xtick.major.width": 0.8,
        "ytick.major.width": 0.8,
    })
    fig, ax = plt.subplots(figsize=(7.4, 4.7), layout="constrained")
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    for column, label, color, marker in SERIES:
        ax.plot(
            users,
            [float(row[column]) for row in rows],
            label=label,
            color=color,
            marker=marker,
            markersize=8,
            markerfacecolor=color,
            markeredgecolor="white",
            markeredgewidth=1.2,
            linewidth=2.2,
            solid_capstyle="round",
        )

    ax.set_xlabel("Users at once")
    ax.set_ylabel("Response time (ms)")
    ax.set_title(
        "cpu workload, 1024 MB, average of three rounds",
        loc="left",
        fontsize=10.5,
        color="#4a4a4a",
        pad=8,
    )
    fig.suptitle(
        "Response time versus users at once",
        x=0.012,
        ha="left",
        fontsize=14,
        color="#1a1a1a",
    )
    ax.set_xticks(users)
    ax.set_xlim(0.4, 8.6)
    ax.set_ylim(1100, 1400)
    ax.set_yticks(range(1100, 1401, 50))
    ax.yaxis.set_major_formatter(lambda value, _pos: f"{value:,.0f}")
    ax.grid(True, axis="y", color="#e6e6e6", linewidth=0.9)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#bdbdbd")
    ax.spines["bottom"].set_color("#bdbdbd")
    ax.tick_params(colors="#333333")
    ax.legend(
        frameon=False,
        loc="upper right",
        handlelength=2.4,
        labelspacing=0.4,
    )
    ax.text(
        0.02,
        0.06,
        "Vertical scale starts at 1,100 ms",
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=8.5,
        color="#6b6b6b",
    )

    FIGURE.parent.mkdir(exist_ok=True)
    fig.savefig(FIGURE, dpi=220)
    plt.close(fig)


def main():
    rows = load_rows()
    plot(rows)
    print(f"Wrote {FIGURE.relative_to(ROOT)}")
    print(f"{'Users':>6}  {'Mean':>8}  {'p95':>8}  {'p99':>8}")
    for row in rows:
        print(
            f"{int(row['users']):6d}  "
            f"{float(row['mean_ms']):8.1f}  "
            f"{float(row['p95_ms']):8.1f}  "
            f"{float(row['p99_ms']):8.1f}"
        )


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, TypeError) as error:
        print(f"Graph failed: {error}", file=sys.stderr)
        sys.exit(1)
