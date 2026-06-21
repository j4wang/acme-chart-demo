"""
Converts an SVG file to PNG using wkhtmltoimage (wraps the SVG in a
minimal HTML shell, since wkhtmltoimage doesn't take SVG directly).

Usage:
    python3 svg_to_png.py output.svg output.png
    python3 svg_to_png.py output.svg output.png --width 2090 --height 1010

If width/height are omitted, they're read from the SVG's width/height
attributes.
"""

import argparse
import re
import subprocess
import tempfile
import os


def read_svg_dimensions(svg_path: str) -> tuple:
    with open(svg_path, "r", encoding="utf-8") as f:
        head = f.read(500)
    w_match = re.search(r'width="(\d+)"', head)
    h_match = re.search(r'height="(\d+)"', head)
    if not (w_match and h_match):
        raise ValueError("Could not find width/height attributes in SVG header")
    return int(w_match.group(1)), int(h_match.group(1))


def convert(svg_path: str, png_path: str, width: int = None, height: int = None):
    if width is None or height is None:
        width, height = read_svg_dimensions(svg_path)

    with open(svg_path, "r", encoding="utf-8") as f:
        svg_content = f.read()

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".html", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write('<html><body style="margin:0">\n')
        tmp.write(svg_content)
        tmp.write("\n</body></html>")
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            [
                "wkhtmltoimage",
                "--width", str(width),
                "--height", str(height),
                tmp_path, png_path,
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"wkhtmltoimage failed:\n{result.stderr}")
    finally:
        os.unlink(tmp_path)


def main():
    ap = argparse.ArgumentParser(description="Convert an SVG file to PNG.")
    ap.add_argument("svg_path")
    ap.add_argument("png_path")
    ap.add_argument("--width", type=int, default=None)
    ap.add_argument("--height", type=int, default=None)
    args = ap.parse_args()

    convert(args.svg_path, args.png_path, args.width, args.height)
    print(f"Wrote {args.png_path}")


if __name__ == "__main__":
    main()
