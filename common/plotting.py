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


# A LinkedIn post shows a figure at about 1200 px across. Figures in this
# series are about 8.6 to 9.4 inches wide, so 140 dpi lands in that window
# and the point sizes above are the sizes a reader actually gets.
FIGURE_DPI = 140


def reserve_footer(figure: plt.Figure) -> None:
    """Keep the disclaimer below the x-axis titles.

    A footer drawn at the bottom of the axes, then saved with a tight bounding
    box, sits on the axis title. The layout rect stops short of the bottom
    edge and the disclaimer occupies that strip.
    """
    engine = figure.get_layout_engine()
    if engine is not None and hasattr(engine, "set"):
        engine.set(rect=(0.0, 0.11, 1.0, 1.0))
    figure.text(
        0.5,
        0.025,
        DISCLAIMER,
        ha="center",
        va="bottom",
        fontsize=8,
        color=COLOURS["muted"],
    )


def save_figure(figure: plt.Figure, path: Path) -> None:
    """Write a PNG. Charts are produced only by this function, never edited."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # No tight bounding box: it would pull the reserved footer strip back
    # onto the axis titles.
    figure.savefig(path, dpi=FIGURE_DPI)
    plt.close(figure)
