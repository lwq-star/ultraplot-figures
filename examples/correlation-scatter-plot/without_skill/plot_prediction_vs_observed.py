r"""Create a 4 x 4 observed-versus-predicted comparison figure.

Run with:
    python plot_prediction_vs_observed.py

The script reads ``data/multiple_data.xlsx`` without modifying it and writes a
PDF and a 600 dpi TIFF next to this script.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from string import ascii_lowercase

import matplotlib as mpl
import numpy as np
import pandas as pd

_gdal_data = Path(sys.prefix) / "Library" / "share" / "gdal"
if _gdal_data.is_dir():
    os.environ.setdefault("GDAL_DATA", str(_gdal_data))

import ultraplot as uplt
from matplotlib.lines import Line2D
from PIL import Image


SCRIPT_DIR = Path(__file__).resolve().parent
INPUT_FILE = SCRIPT_DIR.parent / "data" / "multiple_data.xlsx"
PDF_FILE = SCRIPT_DIR / "prediction_vs_observed_4x4.pdf"
TIFF_FILE = SCRIPT_DIR / "prediction_vs_observed_4x4.tiff"

LAND_TYPES = ("cropland", "forest", "grassland", "savanna")
MODELS = ("LR", "SVR", "GBRT", "DNN")
LAND_COLORS = {
    "cropland": "#D28E2B",
    "forest": "#2A7F62",
    "grassland": "#2F78A8",
    "savanna": "#B5524F",
}


@dataclass(frozen=True)
class PairData:
    observed: np.ndarray
    predicted: np.ndarray
    n_removed: int


@dataclass(frozen=True)
class Metrics:
    n: int
    r2: float
    rmse: float
    bias: float
    slope: float
    intercept: float


def expected_columns() -> list[str]:
    """Return the columns required by the workbook naming convention."""
    return [
        f"{land}{model}_{suffix}"
        for land in LAND_TYPES
        for model in MODELS
        for suffix in (0, 1)
    ]


def read_pairs(path: Path) -> dict[tuple[str, str], PairData]:
    """Read numeric pairs and remove non-finite values pairwise."""
    if not path.is_file():
        raise FileNotFoundError(f"Input workbook not found: {path}")

    frame = pd.read_excel(path, sheet_name="Sheet1")
    missing = sorted(set(expected_columns()) - set(frame.columns))
    if missing:
        raise ValueError("Workbook is missing required columns: " + ", ".join(missing))

    pairs: dict[tuple[str, str], PairData] = {}
    for land in LAND_TYPES:
        for model in MODELS:
            observed = pd.to_numeric(
                frame[f"{land}{model}_0"], errors="coerce"
            ).to_numpy(dtype=float)
            predicted = pd.to_numeric(
                frame[f"{land}{model}_1"], errors="coerce"
            ).to_numpy(dtype=float)
            valid = np.isfinite(observed) & np.isfinite(predicted)
            if valid.sum() < 2:
                raise ValueError(f"Too few valid pairs for {land} / {model}")
            pairs[(land, model)] = PairData(
                observed=observed[valid],
                predicted=predicted[valid],
                n_removed=int((~valid).sum()),
            )
    return pairs


def calculate_metrics(pair: PairData) -> Metrics:
    """Calculate prediction diagnostics for one observed-predicted pair."""
    observed = pair.observed
    predicted = pair.predicted
    residual = predicted - observed
    sst = float(np.sum((observed - observed.mean()) ** 2))
    sse = float(np.sum(residual**2))
    r2 = np.nan if sst == 0 else 1.0 - sse / sst
    slope, intercept = np.polyfit(observed, predicted, deg=1)
    return Metrics(
        n=observed.size,
        r2=float(r2),
        rmse=float(np.sqrt(np.mean(residual**2))),
        bias=float(np.mean(residual)),
        slope=float(slope),
        intercept=float(intercept),
    )


def common_limits(
    pairs: dict[tuple[str, str], PairData], padding_fraction: float = 0.035
) -> tuple[float, float]:
    """Get full-data common limits with a small symmetric visual margin."""
    minimum = min(
        min(pair.observed.min(), pair.predicted.min()) for pair in pairs.values()
    )
    maximum = max(
        max(pair.observed.max(), pair.predicted.max()) for pair in pairs.values()
    )
    span = maximum - minimum
    if span <= 0:
        span = max(abs(maximum), 1.0)
    padding = span * padding_fraction
    return minimum - padding, maximum + padding


def nice_ticks(lower: float, upper: float, target_intervals: int = 5) -> np.ndarray:
    """Return uncluttered ticks shared by every panel."""
    raw_step = (upper - lower) / target_intervals
    magnitude = 10.0 ** np.floor(np.log10(raw_step))
    scaled = raw_step / magnitude
    choices = np.array([1.0, 2.0, 2.5, 5.0, 10.0])
    step = choices[np.argmin(np.abs(choices - scaled))] * magnitude
    start = np.ceil(lower / step) * step
    stop = np.floor(upper / step) * step
    return np.arange(start, stop + 0.5 * step, step)


def metric_text(metric: Metrics) -> str:
    """Create a compact, unit-agnostic panel annotation."""
    return "\n".join(
        (
            f"n = {metric.n:,}",
            rf"$R^2$ = {metric.r2:.3f}",
            f"RMSE = {metric.rmse:.2f}",
            f"Bias = {metric.bias:+.2f}",
            f"Slope = {metric.slope:.3f}",
        )
    )


def make_figure(
    pairs: dict[tuple[str, str], PairData],
    metrics: dict[tuple[str, str], Metrics],
) -> mpl.figure.Figure:
    """Draw the complete multi-panel comparison."""
    lower, upper = common_limits(pairs)
    ticks = nice_ticks(lower, upper)

    mpl.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 7.2,
            "axes.labelsize": 8.2,
            "axes.titlesize": 9.0,
            "xtick.labelsize": 6.8,
            "ytick.labelsize": 6.8,
            "axes.linewidth": 0.65,
            "xtick.major.width": 0.65,
            "ytick.major.width": 0.65,
            "xtick.major.size": 3.0,
            "ytick.major.size": 3.0,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "savefig.facecolor": "white",
        }
    )

    fig, grid = uplt.subplots(
        nrows=4,
        ncols=4,
        figwidth=8.15,
        figheight=8.15,
        share=0,
        span=True,
        wspace=0.13,
        hspace=0.13,
    )
    axes = list(grid)

    for row, land in enumerate(LAND_TYPES):
        for column, model in enumerate(MODELS):
            index = row * len(MODELS) + column
            ax = axes[index]
            pair = pairs[(land, model)]
            metric = metrics[(land, model)]

            ax.scatter(
                pair.observed,
                pair.predicted,
                s=4.6,
                color=LAND_COLORS[land],
                alpha=0.22,
                edgecolors="none",
                rasterized=True,
                zorder=2,
            )
            ax.plot(
                [lower, upper],
                [lower, upper],
                color="#4B4B4B",
                linewidth=0.85,
                linestyle=(0, (4, 2.4)),
                zorder=3,
            )
            fit_x = np.array([pair.observed.min(), pair.observed.max()])
            fit_y = metric.intercept + metric.slope * fit_x
            ax.plot(
                fit_x,
                fit_y,
                color="#7A2942",
                linewidth=1.15,
                zorder=4,
            )

            ax.set_xlim(lower, upper)
            ax.set_ylim(lower, upper)
            ax.set_xticks(ticks)
            ax.set_yticks(ticks)
            ax.set_aspect("equal", adjustable="box")
            ax.grid(False)
            ax.tick_params(direction="out", top=False, right=False, pad=1.8)
            if column > 0:
                ax.tick_params(labelleft=False)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)

            ax.text(
                0.035,
                0.965,
                metric_text(metric),
                transform=ax.transAxes,
                ha="left",
                va="top",
                fontsize=6.15,
                linespacing=1.12,
                color="#202020",
                bbox={
                    "boxstyle": "square,pad=0.20",
                    "facecolor": "white",
                    "edgecolor": "none",
                    "alpha": 0.82,
                },
                zorder=5,
            )
            ax.text(
                0.965,
                0.965,
                f"({ascii_lowercase[index]})",
                transform=ax.transAxes,
                ha="right",
                va="top",
                fontsize=7.0,
                fontweight="bold",
                color="#202020",
                zorder=5,
            )

    grid.format(
        rowlabels=[land.title() for land in LAND_TYPES],
        collabels=list(MODELS),
    )

    fig.supxlabel("Observed value", x=0.53, y=0.012, fontsize=8.2)
    fig.supylabel("Predicted value", x=0.008, y=0.50, fontsize=8.2)

    handles = [
        Line2D(
            [],
            [],
            color="#4B4B4B",
            linewidth=0.85,
            linestyle=(0, (4, 2.4)),
            label="1:1 reference",
        ),
        Line2D(
            [],
            [],
            color="#7A2942",
            linewidth=1.15,
            label="OLS fit",
        ),
    ]
    axes[0].legend(
        handles=handles,
        labels=[handle.get_label() for handle in handles],
        loc="lower right",
        ncols=1,
        frame=True,
        fontsize=6.2,
        handlelength=2.4,
        borderpad=0.25,
        labelspacing=0.25,
        facecolor="white",
        edgecolor="none",
        framealpha=0.82,
    )
    return fig


def ensure_rgb_tiff(path: Path, dpi: int = 600) -> None:
    """Convert the Matplotlib TIFF to publication-friendly RGB in place."""
    with Image.open(path) as image:
        if image.mode == "RGB":
            return
        rgb = image.convert("RGB")
        rgb.save(path, format="TIFF", dpi=(dpi, dpi), compression="tiff_lzw")


def print_summary(
    pairs: dict[tuple[str, str], PairData],
    metrics: dict[tuple[str, str], Metrics],
) -> None:
    """Print data handling and plotted diagnostics for reproducibility."""
    print(f"Input: {INPUT_FILE}")
    print("Non-finite values were removed pairwise within each combination.")
    for land in LAND_TYPES:
        for model in MODELS:
            pair = pairs[(land, model)]
            metric = metrics[(land, model)]
            print(
                f"{land:9s} {model:4s} "
                f"n={metric.n:4d} removed={pair.n_removed:3d} "
                f"R2={metric.r2:.4f} RMSE={metric.rmse:.3f} "
                f"bias={metric.bias:+.3f} slope={metric.slope:.4f}"
            )


def main() -> None:
    pairs = read_pairs(INPUT_FILE)
    metrics = {key: calculate_metrics(pair) for key, pair in pairs.items()}
    print_summary(pairs, metrics)

    figure = make_figure(pairs, metrics)
    figure.savefig(PDF_FILE, dpi=600, bbox_inches="tight")
    figure.savefig(
        TIFF_FILE,
        dpi=600,
        bbox_inches="tight",
        pil_kwargs={"compression": "tiff_lzw"},
    )
    uplt.close(figure)
    ensure_rgb_tiff(TIFF_FILE, dpi=600)
    print(f"PDF:  {PDF_FILE}")
    print(f"TIFF: {TIFF_FILE}")


if __name__ == "__main__":
    main()
