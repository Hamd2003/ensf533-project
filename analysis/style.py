"""Shared look for the report figures: print-sized panels, recessive axes, 95% CI bars."""

import csv
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import font_manager

INK = "#0b0b0b"
MUTED = "#52514e"
GRID = "#e6e5e1"
NEUTRAL = "#9a9893"

# Validated categorical slots (light surface): blue, orange, aqua.
BLUE = "#2a78d6"
ORANGE = "#eb6834"
AQUA = "#1baf7a"

WORKLOAD = {"api": BLUE, "cpu": ORANGE, "data": AQUA}
ROOT = Path(__file__).resolve().parent.parent
FIGURES = ROOT / "analysis" / "figures"
CONFIG = ROOT / "analysis" / "per_config.csv"
RUNS = ROOT / "analysis" / "per_run.csv"

# Full text width of a page, in inches. Panels are sized so 9 pt text prints at 9 pt.
WIDTH = 7.0


def _font():
    installed = {font.name for font in font_manager.fontManager.ttflist}
    for name in ("Helvetica Neue", "Helvetica", "Arial"):
        if name in installed:
            return name
    return "DejaVu Sans"


def apply():
    plt.rcParams.update({
        "font.family": _font(),
        "font.size": 9,
        "axes.titlesize": 9.5,
        "axes.labelsize": 9,
        "xtick.labelsize": 8.5,
        "ytick.labelsize": 8.5,
        "legend.fontsize": 8.5,
        "axes.linewidth": 0.7,
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
        "axes.facecolor": "white",
        "text.color": INK,
        "axes.labelcolor": INK,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "axes.edgecolor": MUTED,
        "axes.titlecolor": INK,
        "errorbar.capsize": 2.5,
    })


def panels(count, height=2.5, width=WIDTH):
    apply()
    fig, axes = plt.subplots(1, count, figsize=(width, height), layout="constrained")
    return fig, ([axes] if count == 1 else list(axes))


def polish(ax, letter, title, xlabel, ylabel):
    """Panel letter and short title on the left; recessive spines and grid."""
    ax.set_title(f"({letter})  {title}", loc="left", pad=6)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.tick_params(length=2.5, width=0.6)
    ax.grid(axis="y", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)


def errorbar(ax, xs, ys, ci, color, label=None, marker="o", line=True, z=3):
    """Point estimate with its 95% CI; a thin line joins the levels of one factor."""
    ax.errorbar(
        xs, ys, yerr=ci,
        color=color, ecolor=color, elinewidth=1.0, capthick=1.0,
        marker=marker, markersize=5, markeredgecolor="white", markeredgewidth=0.8,
        linewidth=1.6 if line else 0, label=label, zorder=z,
    )


def load_configs():
    with CONFIG.open(newline="") as stream:
        return {row["setup"]: row for row in csv.DictReader(stream)}


def load_runs():
    with RUNS.open(newline="") as stream:
        return list(csv.DictReader(stream))


def pick(configs, names):
    missing = [name for name in names if name not in configs]
    if missing:
        raise ValueError(f"per_config.csv is missing {missing}")
    return [configs[name] for name in names]


def values(rows, column):
    return [float(row[column]) for row in rows]


def save(fig, name):
    FIGURES.mkdir(exist_ok=True)
    path = FIGURES / name
    fig.savefig(path, dpi=300)
    plt.close(fig)
    return path
