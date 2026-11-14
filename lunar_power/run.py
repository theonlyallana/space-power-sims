"""Regenerate the figures for the layers that exist.

Run from anywhere:

    python -m lunar_power.run
    python -m lunar_power.run --smoke
    python -m lunar_power.run --layers thermal,electrochemistry

Charts A to D are the fresh cell: the ageing switch does not move them.
Charts E to H are the ageing layer. The scenario block in summary.json is
where ageing changes the capacity and the resistance the earlier layers use.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from common.params import load_params  # noqa: E402
from lunar_power.charts import december, november  # noqa: E402
from lunar_power.scenario import parse_layers, run_scenario  # noqa: E402


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Regenerate the lunar power figures.")
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Reduced November electrochemical runs, written to a temporary directory.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Directory for PNGs. Defaults to lunar_power/figures, or a temp dir in smoke mode.",
    )
    parser.add_argument(
        "--layers",
        default="thermal,electrochemistry,ageing",
        help="Comma-separated layers. safety, pack, variation and mission are not implemented.",
    )
    args = parser.parse_args(argv)
    layers = parse_layers(args.layers)
    if args.out is not None:
        out = args.out
    elif args.smoke:
        out = Path(tempfile.mkdtemp(prefix="lunar-power-smoke-"))
    else:
        out = HERE / "figures"
    out.mkdir(parents=True, exist_ok=True)
    book = load_params(HERE / "params.yaml")

    summary: dict = {"layers": list(layers.enabled())}
    if layers.electrochemistry or layers.thermal:
        summary.update(november.generate(book, out, smoke=args.smoke))
    if layers.ageing and not args.smoke:
        summary.update(december.generate(book, out))
    elif layers.ageing and args.smoke:
        # The December charts are closed-form. Smoke still draws them so a
        # layout failure fails CI. They do not call the slow cell integrator.
        summary.update(december.generate(book, out))
    if not args.smoke:
        summary["scenario"] = run_scenario(book, layers)
        (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        print(f"Wrote figures to {out}")
        if "B" in summary:
            print(f"Chart B relative energy drop, 0 C vs 25 C: {summary['B']['relative_drop'] * 100:.2f}%")
        if "E" in summary:
            print(f"Cycles in one Earth day: {summary['E']['cycles_per_earth_day']:.0f}")
        if summary.get("scenario", {}).get("ageing"):
            lost = summary["scenario"]["ageing"]["capacity_lost_Ah"]
            print(f"Ageing feed, capacity consumed at the stated age: {lost:.3f} Ah")
    else:
        print(f"Smoke figures written to {out}")


if __name__ == "__main__":
    main()
