"""Observed-versus-predicted diagnostics for four land types and four models."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
import json

import matplotlib

matplotlib.use("Agg")

from matplotlib.colors import LogNorm
from matplotlib.lines import Line2D
from matplotlib.ticker import NullLocator
import numpy as np
import pandas as pd
from PIL import Image
import ultraplot as uplt


# ------------------------------- CONFIG ------------------------------------
EXAMPLE_DIR = Path(__file__).resolve().parents[1]
INPUT_XLSX = EXAMPLE_DIR / "data" / "multiple_data.xlsx"
SHEET_NAME = "Sheet1"
OUTPUT_DIR = Path(__file__).resolve().parent
OUTPUT_STEM = "prediction_vs_observed"

LAND_TYPES = ("cropland", "forest", "grassland", "savanna")
LAND_LABELS = {
    "cropland": "Cropland",
    "forest": "Forest",
    "grassland": "Grassland",
    "savanna": "Savanna",
}
MODELS = ("LR", "SVR", "GBRT", "DNN")

JOURNAL = "nat2"
TIFF_DPI = 600
HEXBIN_GRIDSIZE = 32
AXIS_ROUNDING = 5.0
COLORMAP = "viridis"
COLORBAR_LABEL = "Paired observations per hexagon"

REFERENCE_COLOR = "#3A3A3A"
FIT_COLOR = "#D55E00"
REFERENCE_LINESTYLE = (0, (3.0, 2.0))
FIT_LINESTYLE = "-"
LINE_WIDTH = 0.9
ANNOTATION_SIZE = 5.6

FALLBACK_RC = {
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "savefig.facecolor": "white",
    "savefig.transparent": False,
}

PDF_PATH = OUTPUT_DIR / f"{OUTPUT_STEM}.pdf"
TIFF_PATH = OUTPUT_DIR / f"{OUTPUT_STEM}.tif"
PANEL_ROLES = [f"{land}_{model}" for land in LAND_TYPES for model in MODELS]


def _column_name(land_type: str, model: str, role: int) -> str:
    return f"{land_type}{model}_{role}"


def load_pairs(path: Path = INPUT_XLSX, sheet_name: str = SHEET_NAME) -> dict:
    """Load and validate finite observed-predicted pairs from the workbook."""
    if not path.is_file():
        raise FileNotFoundError(f"Input workbook not found: {path}")

    frame = pd.read_excel(path, sheet_name=sheet_name, engine="openpyxl")
    if frame.columns.duplicated().any():
        duplicates = frame.columns[frame.columns.duplicated()].tolist()
        raise ValueError(f"Duplicate workbook columns: {duplicates}")

    expected_columns = [
        _column_name(land, model, role)
        for land in LAND_TYPES
        for model in MODELS
        for role in (0, 1)
    ]
    missing_columns = [column for column in expected_columns if column not in frame]
    if missing_columns:
        raise KeyError(f"Missing required columns: {missing_columns}")

    pairs: dict[str, dict] = {}
    excluded_total = 0
    for land in LAND_TYPES:
        for model in MODELS:
            observed_raw = frame[_column_name(land, model, 0)]
            predicted_raw = frame[_column_name(land, model, 1)]
            observed = pd.to_numeric(observed_raw, errors="coerce").to_numpy(float)
            predicted = pd.to_numeric(predicted_raw, errors="coerce").to_numpy(float)

            nonnumeric_observed = observed_raw.notna().to_numpy() & np.isnan(observed)
            nonnumeric_predicted = predicted_raw.notna().to_numpy() & np.isnan(predicted)
            if nonnumeric_observed.any() or nonnumeric_predicted.any():
                raise ValueError(
                    f"Non-numeric values found in {_column_name(land, model, 0)} "
                    f"or {_column_name(land, model, 1)}."
                )

            valid = np.isfinite(observed) & np.isfinite(predicted)
            excluded = int((~valid).sum())
            excluded_total += excluded
            if valid.sum() < 2:
                raise ValueError(f"Insufficient finite pairs for {land} / {model}.")

            panel = f"{land}_{model}"
            pairs[panel] = {
                "land_type": land,
                "model": model,
                "observed": observed[valid],
                "predicted": predicted[valid],
                "input_count": int(len(frame)),
                "retained_count": int(valid.sum()),
                "excluded_count": excluded,
            }

    input_total = int(len(frame) * len(PANEL_ROLES))
    retained_total = int(sum(item["retained_count"] for item in pairs.values()))
    counts = {
        "input": input_total,
        "retained": retained_total,
        "excluded": excluded_total,
        "excluded_by_class": {
            "incomplete_or_nonfinite_pair": excluded_total,
        },
    }
    if retained_total + excluded_total != input_total:
        raise RuntimeError("Pair accounting does not close.")
    return {"pairs": pairs, "counts": counts, "row_count": int(len(frame))}


def compute_metrics(observed: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    residual = predicted - observed
    denominator = np.sum((observed - observed.mean()) ** 2)
    r2 = np.nan if denominator == 0 else 1.0 - np.sum(residual**2) / denominator
    slope, intercept = np.polyfit(observed, predicted, 1)
    return {
        "n": int(observed.size),
        "r2": float(r2),
        "rmse": float(np.sqrt(np.mean(residual**2))),
        "mae": float(np.mean(np.abs(residual))),
        "bias": float(np.mean(residual)),
        "slope": float(slope),
        "intercept": float(intercept),
    }


def resolve_axis_limits(pairs: dict[str, dict]) -> tuple[float, float]:
    values = np.concatenate(
        [
            np.concatenate((item["observed"], item["predicted"]))
            for item in pairs.values()
        ]
    )
    lower = np.floor(values.min() / AXIS_ROUNDING) * AXIS_ROUNDING
    upper = np.ceil(values.max() / AXIS_ROUNDING) * AXIS_ROUNDING
    if not lower < upper:
        raise ValueError("Cannot resolve a non-zero common axis range.")
    return float(lower), float(upper)


def _colorbar_ticks(max_count: float) -> list[int]:
    candidates = [1, 3, 10, 30, 100, 300, 1000, 3000]
    ticks = [tick for tick in candidates if tick <= max_count]
    return ticks or [1]


def build_figure(path: Path = INPUT_XLSX, sheet_name: str = SHEET_NAME):
    """Build the complete figure and return its descriptive run summary."""
    loaded = load_pairs(path, sheet_name)
    pairs = loaded["pairs"]
    axis_min, axis_max = resolve_axis_limits(pairs)
    fit_x = np.array([axis_min, axis_max], dtype=float)

    hexbins = []
    metrics: dict[str, dict[str, float]] = {}

    with uplt.rc.context(FALLBACK_RC):
        fig, axs = uplt.subplots(nrows=4, ncols=4, journal=JOURNAL)

        for row, land in enumerate(LAND_TYPES):
            for col, model in enumerate(MODELS):
                panel = f"{land}_{model}"
                ax = axs[row * len(MODELS) + col]
                item = pairs[panel]
                observed = item["observed"]
                predicted = item["predicted"]
                panel_metrics = compute_metrics(observed, predicted)
                metrics[panel] = panel_metrics

                density = ax.hexbin(
                    observed,
                    predicted,
                    gridsize=HEXBIN_GRIDSIZE,
                    extent=(axis_min, axis_max, axis_min, axis_max),
                    mincnt=1,
                    cmap=COLORMAP,
                    linewidths=0,
                    rasterized=True,
                )
                hexbins.append(density)
                ax.plot(
                    fit_x,
                    fit_x,
                    color=REFERENCE_COLOR,
                    linestyle=REFERENCE_LINESTYLE,
                    linewidth=LINE_WIDTH,
                    zorder=3,
                )
                ax.plot(
                    fit_x,
                    panel_metrics["slope"] * fit_x + panel_metrics["intercept"],
                    color=FIT_COLOR,
                    linestyle=FIT_LINESTYLE,
                    linewidth=LINE_WIDTH,
                    zorder=4,
                )

                annotation = (
                    f"n = {panel_metrics['n']:,}\n"
                    f"R$^2$ = {panel_metrics['r2']:.3f}\n"
                    f"RMSE = {panel_metrics['rmse']:.2f}\n"
                    f"MAE = {panel_metrics['mae']:.2f}\n"
                    f"Bias = {panel_metrics['bias']:+.2f}"
                )
                ax.text(
                    0.97,
                    0.04,
                    annotation,
                    transform=ax.transAxes,
                    ha="right",
                    va="bottom",
                    fontsize=ANNOTATION_SIZE,
                    linespacing=1.05,
                    bbox={
                        "boxstyle": "square,pad=0.16",
                        "facecolor": "white",
                        "edgecolor": "none",
                    },
                    zorder=5,
                )
                ax.set_xlim(axis_min, axis_max)
                ax.set_ylim(axis_min, axis_max)
                ax.set_aspect("equal", adjustable="box")
        max_count = max(float(hexbin.get_array().max()) for hexbin in hexbins)
        density_norm = LogNorm(vmin=1.0, vmax=max(2.0, max_count))
        for hexbin in hexbins:
            hexbin.set_norm(density_norm)

        colorbar = fig.colorbar(hexbins[0], loc="r", label=COLORBAR_LABEL)
        ticks = _colorbar_ticks(max_count)
        colorbar.set_ticks(ticks)
        colorbar.set_ticklabels([str(tick) for tick in ticks])
        colorbar.ax.yaxis.set_minor_locator(NullLocator())

        legend_handles = [
            Line2D(
                [],
                [],
                color=REFERENCE_COLOR,
                linestyle=REFERENCE_LINESTYLE,
                linewidth=LINE_WIDTH,
            ),
            Line2D(
                [],
                [],
                color=FIT_COLOR,
                linestyle=FIT_LINESTYLE,
                linewidth=LINE_WIDTH,
            ),
        ]
        fig.legend(
            legend_handles,
            ["1:1 reference", "OLS fit"],
            loc="b",
            ncols=2,
            frame=False,
        )

        axs.format(
            abc="a",
            abcloc="ul",
            xlabel="Observed value",
            ylabel="Predicted value",
            grid=False,
        )
        fig.format(
            rowlabels=[LAND_LABELS[land] for land in LAND_TYPES],
            collabels=list(MODELS),
        )

        fig.canvas.draw()
        final_size_mm = tuple((fig.get_size_inches() * 25.4).tolist())

    run_summary = {
        "worksheet_rows": loaded["row_count"],
        "pair_counts": loaded["counts"],
        "axis_limits": [axis_min, axis_max],
        "final_size_mm": final_size_mm,
        "metrics": metrics,
    }
    return fig, run_summary


def save_publication_outputs(
    fig,
    pdf_path: Path = PDF_PATH,
    tiff_path: Path = TIFF_PATH,
    dpi: int = TIFF_DPI,
) -> tuple[Path, Path]:
    """Save a Type 42 PDF and an opaque RGB, LZW-compressed TIFF."""
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    if tiff_path.parent.resolve() != pdf_path.parent.resolve():
        tiff_path.parent.mkdir(parents=True, exist_ok=True)

    with uplt.rc.context(FALLBACK_RC):
        fig.canvas.draw()
        fig.savefig(
            pdf_path,
            format="pdf",
            dpi=dpi,
            facecolor="white",
            transparent=False,
        )
        with BytesIO() as buffer:
            fig.savefig(
                buffer,
                format="png",
                dpi=dpi,
                facecolor="white",
                transparent=False,
            )
            buffer.seek(0)
            with Image.open(buffer) as rendered:
                rgb = rendered.convert("RGB")
                rgb.save(
                    tiff_path,
                    format="TIFF",
                    dpi=(dpi, dpi),
                    compression="tiff_lzw",
                )
                rgb.close()
    return pdf_path, tiff_path


def main() -> None:
    fig, run_summary = build_figure()
    pdf_path, tiff_path = save_publication_outputs(fig)
    summary = {
        "input_workbook": str(INPUT_XLSX),
        "sheet": SHEET_NAME,
        "worksheet_rows": run_summary["worksheet_rows"],
        "pair_counts": run_summary["pair_counts"],
        "axis_limits": run_summary["axis_limits"],
        "final_size_mm": run_summary["final_size_mm"],
        "pdf": str(pdf_path),
        "tiff": str(tiff_path),
        "tiff_dpi": TIFF_DPI,
        "metrics": run_summary["metrics"],
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
