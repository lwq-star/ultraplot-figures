"""Create a publication-ready UltraPlot correlation scatter figure."""

from __future__ import annotations

import string
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import ultraplot as uplt
from matplotlib.lines import Line2D
from matplotlib.figure import Figure as MatplotlibFigure
from PIL import Image


INPUT_FILE = (
    Path(__file__).resolve().parents[1] / "data" / "multiple_data.xlsx"
)
OUTPUT_DIR = Path(__file__).resolve().parent
PNG_FILE = OUTPUT_DIR / "correlation_scatter_ultraplot.png"
PDF_FILE = OUTPUT_DIR / "correlation_scatter_ultraplot.pdf"

SHEET_NAME = "Sheet1"
LAND_COVERS = ("cropland", "forest", "grassland", "savanna")
LAND_LABELS = {
    "cropland": "Cropland",
    "forest": "Forest",
    "grassland": "Grassland",
    "savanna": "Savanna",
}
MODELS = ("DNN", "GBRT", "LR", "SVR")
MODEL_COLORS = {
    "DNN": "#0072B2",
    "GBRT": "#009E73",
    "LR": "#D55E00",
    "SVR": "#CC79A7",
}
FIGURE_SIZE_IN = (8.25, 8.60)
PNG_DPI = 400
AXIS_LIMITS = (-15.0, 90.0)
MAJOR_TICKS = (0, 20, 40, 60, 80)


def load_pairs() -> tuple[pd.DataFrame, dict[tuple[str, str], dict[str, object]]]:
    """Load, validate, and summarize the 16 paired series."""
    if not INPUT_FILE.is_file():
        raise FileNotFoundError(f"Input workbook not found: {INPUT_FILE}")

    frame = pd.read_excel(INPUT_FILE, sheet_name=SHEET_NAME, engine="openpyxl")
    expected = {
        f"{land}{model}_{suffix}"
        for land in LAND_COVERS
        for model in MODELS
        for suffix in (0, 1)
    }
    missing = sorted(expected.difference(frame.columns))
    if missing:
        raise ValueError(f"Workbook is missing required columns: {missing}")

    pairs: dict[tuple[str, str], dict[str, object]] = {}
    for land in LAND_COVERS:
        for model in MODELS:
            x = pd.to_numeric(frame[f"{land}{model}_0"], errors="coerce").to_numpy(float)
            y = pd.to_numeric(frame[f"{land}{model}_1"], errors="coerce").to_numpy(float)
            valid = np.isfinite(x) & np.isfinite(y)
            x = x[valid]
            y = y[valid]
            if x.size < 3 or np.ptp(x) == 0 or np.ptp(y) == 0:
                raise ValueError(f"Insufficient variable paired data for {land}/{model}")

            slope, intercept = np.polyfit(x, y, deg=1)
            pairs[(land, model)] = {
                "x": x,
                "y": y,
                "n": int(x.size),
                "r": float(np.corrcoef(x, y)[0, 1]),
                "slope": float(slope),
                "intercept": float(intercept),
                "x_min": float(x.min()),
                "x_max": float(x.max()),
                "y_min": float(y.min()),
                "y_max": float(y.max()),
            }
    return frame, pairs


def configure_style() -> None:
    """Apply restrained journal-style typography and line settings."""
    uplt.rc.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 7.5,
            "axes.labelsize": 8.0,
            "axes.titlesize": 9.0,
            "axes.linewidth": 0.65,
            "xtick.labelsize": 7.0,
            "ytick.labelsize": 7.0,
            "xtick.major.size": 3.0,
            "ytick.major.size": 3.0,
            "xtick.major.width": 0.65,
            "ytick.major.width": 0.65,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "savefig.facecolor": "white",
        }
    )


def draw_figure(
    pairs: dict[tuple[str, str], dict[str, object]],
) -> tuple[object, object]:
    """Draw the 4-by-4 comparison grid using UltraPlot axes."""
    configure_style()
    fig, axes = uplt.subplots(
        nrows=4,
        ncols=4,
        figsize=FIGURE_SIZE_IN,
        share=False,
        span=False,
        left="0.78in",
        right="0.14in",
        bottom="0.76in",
        top="0.72in",
        wspace="0.16in",
        hspace="0.16in",
    )

    low, high = AXIS_LIMITS
    panel_letters = iter(string.ascii_lowercase)
    for row, land in enumerate(LAND_COVERS):
        for col, model in enumerate(MODELS):
            ax = axes[row, col]
            item = pairs[(land, model)]
            x = item["x"]
            y = item["y"]
            color = MODEL_COLORS[model]

            ax.scatter(
                x,
                y,
                s=5.2,
                c=color,
                alpha=0.22,
                edgecolors="none",
                rasterized=True,
                zorder=2,
            )
            ax.plot(
                [low, high],
                [low, high],
                color="#6B7280",
                linewidth=0.85,
                linestyle=(0, (3.2, 2.4)),
                zorder=1,
            )
            fit_x = np.array([float(np.min(x)), float(np.max(x))])
            fit_y = item["slope"] * fit_x + item["intercept"]
            ax.plot(fit_x, fit_y, color=color, linewidth=1.45, zorder=3)

            ax.set_xlim(low, high)
            ax.set_ylim(low, high)
            ax.set_xticks(MAJOR_TICKS)
            ax.set_yticks(MAJOR_TICKS)
            ax.set_aspect("equal", adjustable="box")
            ax.grid(True, which="major", color="#D9DDE2", linewidth=0.45, alpha=0.72)
            ax.set_axisbelow(True)
            ax.tick_params(
                axis="both",
                which="major",
                direction="out",
                color="#4B5563",
                labelcolor="#222222",
                top=False,
                right=False,
            )
            for spine in ax.spines.values():
                spine.set_color("#4B5563")
                spine.set_linewidth(0.65)

            letter = next(panel_letters)
            ax.text(
                0.035,
                0.965,
                f"({letter})",
                transform=ax.transAxes,
                ha="left",
                va="top",
                fontsize=7.4,
                fontweight="semibold",
                color="#1F2933",
                zorder=5,
            )
            ax.text(
                0.965,
                0.055,
                f"r = {item['r']:.3f}\nn = {item['n']:,}",
                transform=ax.transAxes,
                ha="right",
                va="bottom",
                fontsize=6.8,
                linespacing=1.16,
                color="#20252B",
                bbox={
                    "boxstyle": "square,pad=0.20",
                    "facecolor": "white",
                    "edgecolor": "none",
                    "alpha": 0.84,
                },
                zorder=5,
            )

            if row == 0:
                ax.set_title(model, color=color, fontweight="bold", pad=6)
            if row == len(LAND_COVERS) - 1:
                ax.set_xlabel("_0")
            else:
                ax.tick_params(labelbottom=False)
            if col == 0:
                ax.set_ylabel(f"{LAND_LABELS[land]}\n_1", fontweight="semibold", labelpad=7)
            else:
                ax.tick_params(labelleft=False)

    fig.suptitle(
        "Relationship between paired _0 and _1 values",
        x=0.545,
        y=0.968,
        fontsize=12.2,
        fontweight="semibold",
        color="#151A1F",
    )
    legend_handles = [
        Line2D(
            [0],
            [0],
            marker="o",
            linestyle="none",
            markersize=4.0,
            markerfacecolor="#5F6B76",
            markeredgewidth=0,
            alpha=0.70,
            label="Paired observations",
        ),
        Line2D([0], [0], color="#2F3841", linewidth=1.45, label="OLS fit"),
        Line2D(
            [0],
            [0],
            color="#6B7280",
            linewidth=0.85,
            linestyle=(0, (3.2, 2.4)),
            label="1:1 reference",
        ),
    ]
    MatplotlibFigure.legend(
        fig,
        handles=legend_handles,
        loc="lower center",
        bbox_to_anchor=(0.545, 0.024),
        ncols=3,
        frameon=False,
        fontsize=7.2,
        handlelength=2.5,
        columnspacing=1.8,
    )
    return fig, axes


def main() -> None:
    """Generate PDF and PNG outputs and validate the raster export."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    _, pairs = load_pairs()
    fig, _ = draw_figure(pairs)

    metadata = {
        "Title": "Relationship between paired _0 and _1 values",
        "Subject": "Correlation scatter plots by land cover and model",
        "Creator": "UltraPlot",
        "Producer": "UltraPlot",
        "CreationDate": None,
    }
    fig.savefig(PDF_FILE, dpi=PNG_DPI, facecolor="white", metadata=metadata)
    fig.savefig(
        PNG_FILE,
        dpi=PNG_DPI,
        facecolor="white",
        metadata={"Software": "UltraPlot", "Title": metadata["Title"]},
    )
    plt.close(fig)

    with Image.open(PNG_FILE) as image:
        image.load()
        png_size = image.size
        png_mode = image.mode
        png_dpi = image.info.get("dpi")
    expected_size = tuple(round(value * PNG_DPI) for value in FIGURE_SIZE_IN)
    if png_size != expected_size:
        raise RuntimeError(
            f"Unexpected PNG size {png_size}; expected {expected_size}."
        )
    if png_mode not in {"RGB", "RGBA"}:
        raise RuntimeError(f"Unexpected PNG color mode: {png_mode}")
    if png_dpi is None or any(abs(value - PNG_DPI) > 2 for value in png_dpi[:2]):
        raise RuntimeError(f"Unexpected PNG resolution metadata: {png_dpi}")
    if PDF_FILE.stat().st_size == 0 or PNG_FILE.stat().st_size == 0:
        raise RuntimeError("One or more figure outputs are empty.")
    print(f"Wrote: {PNG_FILE.name}")
    print(f"Wrote: {PDF_FILE.name}")


if __name__ == "__main__":
    main()
