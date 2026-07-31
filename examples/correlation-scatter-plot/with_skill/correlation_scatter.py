from pathlib import Path

import numpy as np
import pandas as pd
import ultraplot as uplt
from matplotlib.lines import Line2D


LAND_COVERS = ("cropland", "forest", "grassland", "savanna")
LAND_LABELS = ("Cropland", "Forest", "Grassland", "Savanna")
MODELS = ("DNN", "GBRT", "LR", "SVR")
MODEL_COLORS = {
    "DNN": "#0072B2",
    "GBRT": "#D55E00",
    "LR": "#009E73",
    "SVR": "#CC79A7",
}
EXPORT_DPI = 1000

OUTPUT_DIR = Path(__file__).resolve().parent
INPUT_FILE = OUTPUT_DIR.parent / "data" / "multiple_data.xlsx"
PDF_FILE = OUTPUT_DIR / "correlation_scatter.pdf"
PNG_FILE = OUTPUT_DIR / "correlation_scatter.png"


def load_pairs():
    if not INPUT_FILE.is_file():
        raise FileNotFoundError(f"Input workbook not found: {INPUT_FILE}")

    data = pd.read_excel(INPUT_FILE, sheet_name="Sheet1")
    required = [
        f"{land}{model}_{suffix}"
        for land in LAND_COVERS
        for model in MODELS
        for suffix in (0, 1)
    ]
    missing_columns = sorted(set(required).difference(data.columns))
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    pairs = {}
    all_values = []
    for land in LAND_COVERS:
        for model in MODELS:
            x_name = f"{land}{model}_0"
            y_name = f"{land}{model}_1"
            if not pd.api.types.is_numeric_dtype(data[x_name]):
                raise TypeError(f"Column is not numeric: {x_name}")
            if not pd.api.types.is_numeric_dtype(data[y_name]):
                raise TypeError(f"Column is not numeric: {y_name}")
            if not data[x_name].isna().equals(data[y_name].isna()):
                raise ValueError(f"Unpaired missing values in {x_name} and {y_name}")

            pair = data[[x_name, y_name]].dropna().to_numpy(dtype=float)
            if pair.shape[0] < 2:
                raise ValueError(f"Too few paired observations for {land} {model}")
            if not np.isfinite(pair).all():
                raise ValueError(f"Non-finite values found for {land} {model}")

            pairs[(land, model)] = (pair[:, 0], pair[:, 1])
            all_values.append(pair.ravel())

    values = np.concatenate(all_values)
    lower = 10 * np.floor(values.min() / 10)
    upper = 10 * np.ceil(values.max() / 10)
    if lower == upper:
        lower -= 10
        upper += 10
    return pairs, (float(lower), float(upper))


def main():
    pairs, limits = load_pairs()

    with uplt.rc.context({"font.size": 8}):
        fig, axs = uplt.subplots(
            nrows=len(LAND_COVERS),
            ncols=len(MODELS),
            journal="nat2",
            share=True,
            refaspect=1,
        )

        for row, land in enumerate(LAND_COVERS):
            for col, model in enumerate(MODELS):
                ax = axs[row, col]
                x, y = pairs[(land, model)]
                color = MODEL_COLORS[model]

                ax.plot(
                    limits,
                    limits,
                    color="0.45",
                    linestyle="--",
                    linewidth=0.8,
                    zorder=1,
                )
                ax.scatter(
                    x,
                    y,
                    s=3.5,
                    color=color,
                    alpha=0.22,
                    edgecolors="none",
                    rasterized=True,
                    zorder=2,
                )

                slope, intercept = np.polyfit(x, y, 1)
                fit_x = np.array([x.min(), x.max()])
                ax.plot(
                    fit_x,
                    slope * fit_x + intercept,
                    color=color,
                    linewidth=1.4,
                    zorder=3,
                )

                correlation = np.corrcoef(x, y)[0, 1]
                ax.text(
                    0.96,
                    0.05,
                    f"$r$ = {correlation:.2f}\n$n$ = {x.size:,}",
                    transform=ax.transAxes,
                    ha="right",
                    va="bottom",
                    fontsize=6.7,
                    linespacing=1.15,
                    bbox={
                        "boxstyle": "square,pad=0.16",
                        "facecolor": "white",
                        "edgecolor": "none",
                        "alpha": 0.84,
                    },
                    zorder=4,
                )

        axs.format(
            abc="a.",
            abcloc="ul",
            toplabels=MODELS,
            leftlabels=LAND_LABELS,
            xlabel="_0",
            ylabel="_1",
            xlim=limits,
            ylim=limits,
            xlocator=20,
            ylocator=20,
            xminorlocator=10,
            yminorlocator=10,
            grid=False,
        )

        legend_handles = [
            Line2D([0], [0], color="0.15", linewidth=1.4, label="OLS fit"),
            Line2D(
                [0],
                [0],
                color="0.45",
                linestyle="--",
                linewidth=0.8,
                label="1:1 line",
            ),
        ]
        fig.legend(handles=legend_handles, loc="b", ncols=2, frame=False)
        fig.save(PDF_FILE, dpi=EXPORT_DPI)
        fig.save(PNG_FILE, dpi=EXPORT_DPI)


if __name__ == "__main__":
    main()
