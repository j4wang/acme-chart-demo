"""
Entry point: generates the swimlane SVG from a process-steps CSV.

Usage:
    python3 generate.py input.csv output.svg
    python3 generate.py input.csv output.svg --png output.png
"""

import sys
import argparse
from parser import parse_csv
from layout import compute_layout
from renderer import render_svg

DEFAULT_TITLE = "Acme Corp Expense Reimbursement: Current State"
DEFAULT_LANE_ORDER = ["Employee", "Manager", "Finance", "System"]


def main():
    ap = argparse.ArgumentParser(description="Generate a swimlane diagram from a process CSV.")
    ap.add_argument("input_csv", nargs="?", default="input.csv")
    ap.add_argument("output_svg", nargs="?", default="output.svg")
    ap.add_argument("--png", default=None, help="Also write a PNG to this path")
    args = ap.parse_args()

    model = parse_csv(args.input_csv)

    if set(DEFAULT_LANE_ORDER) == set(model.lanes):
        lane_order = DEFAULT_LANE_ORDER
    else:
        lane_order = model.lanes

    layout = compute_layout(model, lane_order=lane_order)
    svg = render_svg(model, layout, title=DEFAULT_TITLE)

    with open(args.output_svg, "w", encoding="utf-8") as f:
        f.write(svg)

    print(f"Wrote {args.output_svg} ({layout.width}x{layout.height})")

    if args.png:
        from svg_to_png import convert
        convert(args.output_svg, args.png, layout.width, layout.height)
        print(f"Wrote {args.png}")


if __name__ == "__main__":
    main()

