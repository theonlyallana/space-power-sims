"""Regenerate the November figures from params.yaml.

Run from anywhere:

    python 01-lunar-night-battery/run_all.py
    python 01-lunar-night-battery/run_all.py --smoke

Smoke mode is what CI uses. It checks that the scripts execute, writes to a
temporary directory, and does not touch the committed PNGs. The full run is
what produces figures/ and summary.json.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for path in (ROOT, HERE):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from common.params import load_params  # noqa: E402
from make_figures import generate  # noqa: E402


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Regenerate the November lunar-night figures.")
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Reduced electrochemical runs, written to a temporary directory.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Directory for PNGs. Defaults to figures/ or a temp dir in smoke mode.",
    )
    args = parser.parse_args(argv)
    if args.out is not None:
        out = args.out
    elif args.smoke:
        out = Path(tempfile.mkdtemp(prefix="lunar-night-smoke-"))
    else:
        out = HERE / "figures"
    book = load_params(HERE / "params.yaml")
    summary = generate(book, out, smoke=args.smoke)
    print(f"Wrote figures to {out}")
    if not args.smoke:
        drop = summary["B"]["relative_drop"]
        print(f"Chart B relative energy drop, 0 C vs 25 C: {drop * 100:.2f}%")
        print(f"Chart D keep-warm empty at hour: {summary['D']['keep_warm_empty_h']}")
        print(f"Chart D hibernate final temperature C: {summary['D']['hibernate_final_C']:.1f}")


if __name__ == "__main__":
    main()
