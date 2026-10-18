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
import matplotlib.ticker as ticker

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
    """Keep the disclaimer in a band under the axes.

    Constrained layout's rectangle is (left, bottom, width, height), not
    (left, bottom, right, top). A height of 1 with the bottom raised pushes
    the titles off the top of the canvas. This rectangle runs from y = 0.055
    to y = 1, and the disclaimer sits in the strip below that.
    """
    engine = figure.get_layout_engine()
    if engine is not None and hasattr(engine, "set"):
        # (left, bottom, width, height). The top stays at 1 so titles are
        # not pushed off the canvas. The bottom band is the disclaimer.
        # A slightly larger h_pad keeps the suptitle off the figure edge.
        engine.set(rect=(0.0, 0.055, 1.0, 0.945), h_pad=0.12)
    figure.text(
        0.5,
        0.02,
        DISCLAIMER,
        ha="center",
        va="bottom",
        fontsize=8,
        color=COLOURS["muted"],
    )


def texts_outside_figure(figure: plt.Figure, tolerance_px: float = 1.0) -> list[str]:
    """Text whose window extent crosses the canvas edge.

    Tick labels, titles, legends and the footer are all Text artists. A
    layout that shoves a title off the top of the figure fails this check.
    """
    figure.canvas.draw()
    renderer = figure.canvas.get_renderer()
    width, height = figure.canvas.get_width_height()
    outside = []
    for artist in figure.findobj(match=lambda item: isinstance(item, matplotlib.text.Text)):
        if not artist.get_visible():
            continue
        content = artist.get_text().strip()
        if not content:
            continue
        boxes = [artist.get_window_extent(renderer=renderer)]
        patch = artist.get_bbox_patch()
        if patch is not None:
            boxes.append(patch.get_window_extent(renderer=renderer))
        for box in boxes:
            if (
                box.x0 < -tolerance_px
                or box.y0 < -tolerance_px
                or box.x1 > width + tolerance_px
                or box.y1 > height + tolerance_px
            ):
                outside.append(content.replace("\n", " ")[:80])
                break
    return outside


def keep_tick_labels_inside(figure: plt.Figure) -> None:
    """Drop major ticks that sit outside the view.

    The locator happily returns a tick past the data limit. That label is
    drawn unclipped, so it walks off the canvas (a −30 °C tick beside data
    that starts at −20 °C, a 4.2 V tick above a 4.1 V axis). Ticks inside
    the view stay on the automatic formatter.
    """
    for axis in figure.axes:
        for dimension in (axis.xaxis, axis.yaxis):
            lo, hi = dimension.get_view_interval()
            if lo > hi:
                lo, hi = hi, lo
            span = hi - lo
            if not (span > 0) or not (span < float("inf")):
                continue
            locator = dimension.get_major_locator()
            try:
                values = [float(value) for value in locator.tick_values(lo, hi)]
            except Exception:
                continue
            epsilon = span * 1e-6
            inside = [value for value in values if lo - epsilon <= value <= hi + epsilon]
            if len(inside) < 2 or len(inside) == len(values):
                continue
            dimension.set_major_locator(ticker.FixedLocator(inside))


def save_figure(figure: plt.Figure, path: Path) -> None:
    """Write a PNG. Charts are produced only by this function, never edited.

    The canvas is saved whole. A tight bounding box would crop the footer
    band back onto the axis titles, which is how the disclaimer ended up on
    the x-axis label.
    """
    keep_tick_labels_inside(figure)
    outside = texts_outside_figure(figure)
    if outside:
        raise RuntimeError("text falls outside the figure: " + "; ".join(outside))
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=FIGURE_DPI)
    plt.close(figure)
