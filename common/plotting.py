"""One plotting style for every chart in the series.

LinkedIn shrinks figures, so lines are thick, type is large, and the colours
are the Okabe-Ito set, which stays distinct in greyscale and for the most
common kinds of colour-blindness. A one-line footer carries the disclaimer
onto the image itself, because the image is what gets posted.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Okabe-Ito, in an order that reads well as warm versus cold.
COLOURS = {
    "warm": "#D55E00",
    "mid": "#0072B2",
    "cold": "#009E73",
    "ink": "#222222",
    "muted": "#666666",
    "rhu": "#CC79A7",
    "second": "#E69F00",
}

DISCLAIMER = (
    "Personal project using only public data. "
    "Not affiliated with or endorsed by my employer."
)


def apply_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 12,
            "axes.labelsize": 13,
            "axes.titlesize": 13,
            "legend.fontsize": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.linewidth": 0.8,
            "xtick.direction": "out",
            "ytick.direction": "out",
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
            "lines.linewidth": 2.2,
        }
    )


def save_figure(figure: plt.Figure, path: Path) -> None:
    """Write a PNG. Charts are produced only by this function, never edited."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(figure)
