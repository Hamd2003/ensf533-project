"""Validity figure: Little's Law on every run, and the speed spread between Lambda
execution environments inside each run.

Panel (a) reads analysis/per_run.csv. Panel (b) reads the raw k6 lines in
results/round*/k6-measured-data/, because per-environment timing is not in the
shared tables. It uses measured, warm requests and environments with at least
10 of them, and compares the function work time each environment reports.
"""

import collections
import json
import statistics
import sys

from style import (
    BLUE, MUTED, NEUTRAL, ORANGE, ROOT, AQUA, load_runs, panels, polish, save,
)

ROUND_COLOR = {1: BLUE, 2: ORANGE, 3: AQUA}
SHIFT = {1: -0.2, 2: 0.0, 3: 0.2}
SETUPS = ("api-512", "api-1024", "api-1769", "cpu-512", "cpu-1024", "cpu-1769",
          "data-512", "data-1024", "data-1769", "cpu-1024-low", "cpu-1024-high")
MULTI = ("cpu-512", "cpu-1024", "cpu-1769", "cpu-1024-high",
         "data-512", "data-1024", "data-1769")
LABEL = {"cpu-1024-low": "cpu-1024 (1 user)", "cpu-1024-high": "cpu-1024 (8 users)"}
MIN_REQUESTS = 10


def environment_ratio(round_number, setup):
    """Slowest / fastest mean work time across one run's execution environments."""
    path = (ROOT / "results" / f"round{round_number}" / "k6-measured-data"
            / f"restricted-r{round_number}-{setup}.jsonl")
    by_env = collections.defaultdict(list)
    for line in path.read_text().splitlines():
        request = json.loads(line)
        if request["phase"] == "measure" and not request["cold"]:
            by_env[request["env_id"]].append(float(request["compute_ms"]))
    means = sorted(statistics.mean(v) for v in by_env.values() if len(v) >= MIN_REQUESTS)
    if len(means) < 2:
        raise ValueError(f"{path.name}: fewer than two environments with {MIN_REQUESTS} requests")
    return means[-1] / means[0]


def legend_rounds(ax):
    for number, color in ROUND_COLOR.items():
        ax.scatter([], [], s=14, color=color, label=f"round {number}")
    ax.legend(loc="upper right", ncol=3, frameon=False, labelcolor=MUTED,
              handletextpad=0.2, columnspacing=0.8)


def littles_law(ax, runs):
    if len(runs) != 33:
        raise ValueError(f"Expected 33 runs, found {len(runs)}")
    for run in runs:
        number = int(run["round"])
        gap = (float(run["littles_law"]) - int(run["users"])) / int(run["users"]) * 100
        ax.scatter(SETUPS.index(run["setup"]) + SHIFT[number], gap, s=12,
                   color=ROUND_COLOR[number], zorder=3, linewidth=0)
    ax.axhline(0, color=NEUTRAL, linewidth=0.8, zorder=1)
    ax.set_xticks(range(len(SETUPS)), [LABEL.get(s, s) for s in SETUPS],
                  rotation=60, ha="right", rotation_mode="anchor", fontsize=7.5)
    ax.set_ylim(-2, 2)
    legend_rounds(ax)
    polish(ax, "a", "Little's Law: X·R vs. users (limit ±10%)", "", "Gap (%)")


def environments(ax):
    ratios = []
    for index, setup in enumerate(MULTI):
        for number in (1, 2, 3):
            ratio = environment_ratio(number, setup)
            ratios.append(ratio)
            ax.scatter(index + SHIFT[number], (ratio - 1) * 100, s=12,
                       color=ROUND_COLOR[number], zorder=3, linewidth=0)
    ax.set_xticks(range(len(MULTI)), [LABEL.get(s, s) for s in MULTI],
                  rotation=60, ha="right", rotation_mode="anchor", fontsize=7.5)
    ax.set_ylim(0, 40)
    legend_rounds(ax)
    polish(ax, "b", "Slowest vs. fastest environment", "", "Extra work time (%)")
    return ratios


def main():
    fig, axes = panels(2, height=2.6)
    littles_law(axes[0], load_runs())
    ratios = environments(axes[1])
    path = save(fig, "graph4_validity.png")
    print(f"Wrote {path.relative_to(ROOT)}")
    print(f"Environment spread: median {(statistics.median(ratios) - 1) * 100:.0f}%, "
          f"max {(max(ratios) - 1) * 100:.0f}%, "
          f"{sum(r > 1.15 for r in ratios)} of {len(ratios)} runs above 15%")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, TypeError) as error:
        print(f"Graph failed: {error}", file=sys.stderr)
        sys.exit(1)
