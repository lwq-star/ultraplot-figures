"""Validate final PDF and PNG figure files without writing artifacts."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

from PIL import Image
from pypdf import PdfReader


MM_PER_INCH = 25.4
POINTS_PER_INCH = 72.0


def pdf_size(path: Path) -> tuple[float, float]:
    reader = PdfReader(path)
    if len(reader.pages) != 1:
        raise ValueError(f"Expected one PDF page, found {len(reader.pages)}.")
    box = reader.pages[0].mediabox
    return float(box.width) / POINTS_PER_INCH, float(box.height) / POINTS_PER_INCH


def png_properties(path: Path) -> tuple[tuple[int, int], tuple[float, float] | None]:
    with Image.open(path) as image:
        image.verify()
    with Image.open(path) as image:
        size = tuple(map(int, image.size))
        dpi = image.info.get("dpi")
    if dpi is None:
        return size, None
    return size, (float(dpi[0]), float(dpi[1]))


def close(actual: float, expected: float, tolerance: float) -> bool:
    return math.isfinite(actual) and abs(actual - expected) <= tolerance


def validate(args: argparse.Namespace) -> list[str]:
    failures: list[str] = []
    pdf_inches: tuple[float, float] | None = None
    png_size: tuple[int, int] | None = None

    for path in (args.pdf, args.png):
        if path is not None and (not path.is_file() or path.stat().st_size == 0):
            failures.append(f"Missing or empty output: {path}")

    if failures:
        return failures

    if args.pdf is not None:
        try:
            pdf_inches = pdf_size(args.pdf)
        except Exception as error:
            failures.append(f"Invalid PDF {args.pdf}: {error}")
        else:
            width_mm = pdf_inches[0] * MM_PER_INCH
            if args.expected_width_mm is not None and not close(
                width_mm, args.expected_width_mm, args.width_tolerance_mm
            ):
                failures.append(
                    f"PDF width is {width_mm:.4f} mm; expected "
                    f"{args.expected_width_mm:.4f} +/- {args.width_tolerance_mm:.4f} mm."
                )

    if args.png is not None:
        try:
            png_size, png_dpi = png_properties(args.png)
        except Exception as error:
            failures.append(f"Invalid PNG {args.png}: {error}")
        else:
            if png_dpi is None:
                failures.append("PNG has no resolution metadata.")
            elif not all(
                close(value, args.expected_dpi, args.dpi_tolerance) for value in png_dpi
            ):
                failures.append(
                    f"PNG resolution is {png_dpi}; expected {args.expected_dpi} "
                    f"+/- {args.dpi_tolerance} dpi."
                )

            if args.expected_width_mm is not None:
                expected_width_px = (
                    args.expected_width_mm / MM_PER_INCH * args.expected_dpi
                )
                if abs(png_size[0] - expected_width_px) > args.pixel_tolerance:
                    failures.append(
                        f"PNG width is {png_size[0]} px; expected approximately "
                        f"{expected_width_px:.1f} px."
                    )

    if pdf_inches is not None and png_size is not None:
        expected_pixels = tuple(value * args.expected_dpi for value in pdf_inches)
        for axis, actual, expected in zip(
            "width height".split(), png_size, expected_pixels
        ):
            if abs(actual - expected) > args.pixel_tolerance:
                failures.append(
                    f"PNG {axis} is {actual} px; PDF size implies approximately "
                    f"{expected:.1f} px at {args.expected_dpi} dpi."
                )

    return failures


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path)
    parser.add_argument("--png", type=Path)
    parser.add_argument("--expected-width-mm", type=float)
    parser.add_argument("--expected-dpi", type=float, default=1000.0)
    parser.add_argument("--width-tolerance-mm", type=float, default=0.2)
    parser.add_argument("--dpi-tolerance", type=float, default=2.0)
    parser.add_argument("--pixel-tolerance", type=float, default=3.0)
    args = parser.parse_args()
    if args.pdf is None and args.png is None:
        parser.error("provide --pdf, --png, or both")
    return args


def main() -> None:
    args = parse_args()
    failures = validate(args)
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        raise SystemExit(1)
    checked = ", ".join(str(path) for path in (args.pdf, args.png) if path is not None)
    print(f"PASS: {checked}")


if __name__ == "__main__":
    main()
