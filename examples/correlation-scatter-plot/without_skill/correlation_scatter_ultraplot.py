from __future__ import annotations

import math
from pathlib import Path

import matplotlib as mpl

mpl.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.axes import Axes
from matplotlib.ticker import FixedLocator
import numpy as np
import pandas as pd
from scipy import stats
import ultraplot as uplt


OUTPUT_DIR = Path(__file__).resolve().parent
INPUT_FILE = OUTPUT_DIR.parent / "data" / "multiple_data.xlsx"
PNG_FILE = OUTPUT_DIR / "correlation_scatter.png"
PDF_FILE = OUTPUT_DIR / "correlation_scatter.pdf"
STATS_FILE = OUTPUT_DIR / "correlation_statistics.csv"

LAND_COVERS = ("cropland", "forest", "grassland", "savanna")
MODELS = ("DNN", "GBRT", "LR", "SVR")
MODEL_COLORS = {
    "DNN": "#0072B2",
    "GBRT": "#D55E00",
    "LR": "#CC79A7",
    "SVR": "#009E73",
}


def nice_limits(data_min: float, data_max: float, target_ticks: int = 6):
    """Return shared rounded limits and ticks that include every observation."""
    span = data_max - data_min
    rough_step = span / max(target_ticks - 1, 1)
    magnitude = 10 ** math.floor(math.log10(rough_step))
    normalized = rough_step / magnitude
    if normalized <= 1:
        multiplier = 1
    elif normalized <= 2:
        multiplier = 2
    elif normalized <= 5:
        multiplier = 5
    else:
        multiplier = 10
    step = multiplier * magnitude
    lower = math.floor(data_min / step) * step
    upper = math.ceil(data_max / step) * step
    ticks = np.arange(lower, upper + step * 0.5, step)
    return float(lower), float(upper), ticks


def panel_statistics(x: np.ndarray, y: np.ndarray) -> dict[str, float]:
    fit = stats.linregress(x, y)
    pearson = stats.pearsonr(x, y)
    spearman = stats.spearmanr(x, y)
    residual = y - x
    degrees_freedom = x.size - 2
    t_critical = stats.t.ppf(0.975, degrees_freedom)
    return {
        "n": int(x.size),
        "pearson_r": float(pearson.statistic),
        "pearson_p": float(pearson.pvalue),
        "spearman_rho": float(spearman.statistic),
        "spearman_p": float(spearman.pvalue),
        "ols_slope": float(fit.slope),
        "ols_slope_ci_low": float(fit.slope - t_critical * fit.stderr),
        "ols_slope_ci_high": float(fit.slope + t_critical * fit.stderr),
        "ols_intercept": float(fit.intercept),
        "ols_r_squared": float(fit.rvalue**2),
        "rmse_to_identity": float(np.sqrt(np.mean(residual**2))),
        "mae_to_identity": float(np.mean(np.abs(residual))),
        "x_min": float(np.min(x)),
        "x_max": float(np.max(x)),
        "y_min": float(np.min(y)),
        "y_max": float(np.max(y)),
    }


def load_and_validate():
    dataframe = pd.read_excel(INPUT_FILE, sheet_name="Sheet1")
    expected = [
        f"{land}{model}_{suffix}"
        for land in LAND_COVERS
        for model in MODELS
        for suffix in (0, 1)
    ]
    missing_columns = sorted(set(expected) - set(dataframe.columns))
    if missing_columns:
        raise ValueError(f"Missing expected columns: {missing_columns}")

    panels: dict[tuple[str, str], tuple[np.ndarray, np.ndarray]] = {}
    rows: list[dict[str, float | int | str | bool]] = []
    all_values: list[np.ndarray] = []

    for land in LAND_COVERS:
        reference_x: np.ndarray | None = None
        for model in MODELS:
            x_column = f"{land}{model}_0"
            y_column = f"{land}{model}_1"
            x_raw = dataframe[x_column]
            y_raw = dataframe[y_column]
            incomplete_pair_count = int((x_raw.isna() ^ y_raw.isna()).sum())
            if incomplete_pair_count:
                raise ValueError(
                    f"{land}/{model} has {incomplete_pair_count} one-sided missing pairs"
                )

            pair = dataframe[[x_column, y_column]].dropna()
            x = pair[x_column].to_numpy(dtype=float)
            y = pair[y_column].to_numpy(dtype=float)
            if x.size < 3:
                raise ValueError(f"{land}/{model} has fewer than three complete pairs")
            if not (np.isfinite(x).all() and np.isfinite(y).all()):
                raise ValueError(f"{land}/{model} contains non-finite values")

            if reference_x is None:
                reference_x = x
            x_matches_first_model = bool(np.array_equal(reference_x, x))
            panels[(land, model)] = (x, y)
            all_values.extend((x, y))

            row: dict[str, float | int | str | bool] = {
                "land_cover": land,
                "model": model,
                "source_rows": int(len(dataframe)),
                "complete_pairs": int(x.size),
                "missing_pairs": int(len(dataframe) - x.size),
                "one_sided_missing_pairs": incomplete_pair_count,
                "x_matches_first_model_within_land": x_matches_first_model,
            }
            row.update(panel_statistics(x, y))
            rows.append(row)

    summary = pd.DataFrame(rows)
    combined = np.concatenate(all_values)
    limits = nice_limits(float(combined.min()), float(combined.max()))
    return dataframe, panels, summary, limits


def make_figure(
    panels: dict[tuple[str, str], tuple[np.ndarray, np.ndarray]],
    summary: pd.DataFrame,
    limits: tuple[float, float, np.ndarray],
):
    mpl.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 7.5,
            "axes.labelsize": 9,
            "axes.titlesize": 9.5,
            "xtick.labelsize": 7,
            "ytick.labelsize": 7,
            "axes.linewidth": 0.65,
            "xtick.major.width": 0.65,
            "ytick.major.width": 0.65,
            "xtick.major.size": 3,
            "ytick.major.size": 3,
            "savefig.transparent": False,
        }
    )

    fig, subplot_grid = uplt.subplots(
        nrows=4,
        ncols=4,
        sharex=True,
        sharey=True,
        figsize=(7.55, 7.35),
    )
    axes = np.asarray(list(subplot_grid), dtype=object).reshape(4, 4)
    lower, upper, ticks = limits

    for row_index, land in enumerate(LAND_COVERS):
        for column_index, model in enumerate(MODELS):
            ax = axes[row_index, column_index]
            x, y = panels[(land, model)]
            record = summary[
                (summary["land_cover"] == land) & (summary["model"] == model)
            ].iloc[0]
            color = MODEL_COLORS[model]

            ax.plot(
                [lower, upper],
                [lower, upper],
                color="#4D4D4D",
                linewidth=0.8,
                linestyle=(0, (3.2, 2.2)),
                zorder=1,
            )
            ax.scatter(
                x,
                y,
                s=5.0,
                color=color,
                alpha=0.20,
                edgecolors="none",
                rasterized=True,
                zorder=2,
            )
            fit_x = np.array([x.min(), x.max()])
            fit_y = record["ols_slope"] * fit_x + record["ols_intercept"]
            ax.plot(fit_x, fit_y, color=color, linewidth=1.35, zorder=3)

            panel_letter = chr(ord("a") + row_index * 4 + column_index)
            ax.text(
                0.035,
                0.955,
                f"({panel_letter})",
                transform=ax.transAxes,
                ha="left",
                va="top",
                fontsize=7.5,
                fontweight="bold",
                color="#222222",
                zorder=5,
            )
            ax.text(
                0.965,
                0.045,
                rf"$r$ = {record['pearson_r']:.3f}"
                + "\n"
                + rf"$b$ = {record['ols_slope']:.3f}"
                + "\n"
                + rf"$n$ = {int(record['n']):,}",
                transform=ax.transAxes,
                ha="right",
                va="bottom",
                fontsize=6.7,
                linespacing=1.15,
                color="#222222",
                bbox={
                    "boxstyle": "square,pad=0.20",
                    "facecolor": "white",
                    "edgecolor": "none",
                    "alpha": 0.84,
                },
                zorder=5,
            )

            ax.set_xlim(lower, upper)
            ax.set_ylim(lower, upper)
            ax.set_aspect("equal", adjustable="box")
            ax.xaxis.set_major_locator(FixedLocator(ticks))
            ax.yaxis.set_major_locator(FixedLocator(ticks))
            ax.grid(True, color="#D9D9D9", linewidth=0.45, alpha=0.72, zorder=0)
            ax.tick_params(direction="out", colors="#333333")
            for spine in ax.spines.values():
                spine.set_color("#4A4A4A")
                spine.set_linewidth(0.65)

            if row_index == 0:
                ax.set_title(model, color=color, fontweight="bold", pad=5)
            if column_index == 3:
                ax.text(
                    1.055,
                    0.5,
                    land.title(),
                    transform=ax.transAxes,
                    ha="left",
                    va="center",
                    rotation=-90,
                    fontsize=8.5,
                    fontweight="bold",
                    color="#333333",
                    clip_on=False,
                )

    fig.suptitle(
        "Relationships between _0 and _1 by land cover and model",
        x=0.5,
        y=0.995,
        fontsize=11,
        fontweight="bold",
        color="#222222",
    )
    fig.supxlabel("_0", x=0.5, y=0.012, fontsize=9.5, fontweight="bold")
    fig.supylabel("_1", x=0.012, y=0.5, fontsize=9.5, fontweight="bold")

    legend_handles = [
        Line2D(
            [0],
            [0],
            color="#555555",
            linewidth=1.35,
            label="OLS fit (model color)",
        ),
        Line2D(
            [0],
            [0],
            color="#4D4D4D",
            linewidth=0.8,
            linestyle=(0, (3.2, 2.2)),
            label="1:1 line",
        ),
    ]
    Axes.legend(
        axes[0, 0],
        handles=legend_handles,
        loc="upper right",
        frameon=True,
        framealpha=0.88,
        facecolor="white",
        edgecolor="none",
        fontsize=6.2,
        handlelength=2.2,
        borderpad=0.35,
        labelspacing=0.3,
    )
    return fig


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    dataframe, panels, summary, limits = load_and_validate()
    summary.to_csv(STATS_FILE, index=False, float_format="%.10g")
    fig = make_figure(panels, summary, limits)
    metadata = {
        "Title": "Relationships between _0 and _1 by land cover and model",
        "Author": "Reproducible UltraPlot workflow",
        "Subject": "Correlation scatter plots with OLS and 1:1 reference lines",
    }
    fig.savefig(PNG_FILE, dpi=400, bbox_inches="tight", pad_inches=0.045)
    fig.savefig(PDF_FILE, dpi=400, bbox_inches="tight", pad_inches=0.045, metadata=metadata)
    plt.close(fig)

    print(f"Input shape: {dataframe.shape[0]} rows x {dataframe.shape[1]} columns")
    print("Complete pairs by land/model:")
    print(summary[["land_cover", "model", "complete_pairs"]].to_string(index=False))
    print(
        "Shared plotting limits: "
        f"{limits[0]:g} to {limits[1]:g}; ticks={limits[2].tolist()}"
    )
    print(f"Wrote: {PNG_FILE}")
    print(f"Wrote: {PDF_FILE}")
    print(f"Wrote: {STATS_FILE}")


if __name__ == "__main__":
    main()
