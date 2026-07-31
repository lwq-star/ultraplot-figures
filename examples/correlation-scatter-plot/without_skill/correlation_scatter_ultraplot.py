from pathlib import Path

import matplotlib as mpl
import numpy as np
import pandas as pd
import ultraplot as uplt
from matplotlib.lines import Line2D
from matplotlib.ticker import MultipleLocator


OUTPUT_DIR = Path(__file__).resolve().parent
DATA_PATH = OUTPUT_DIR.parent / "data" / "multiple_data.xlsx"
PNG_PATH = OUTPUT_DIR / "correlation_scatter_ultraplot.png"
PDF_PATH = OUTPUT_DIR / "correlation_scatter_ultraplot.pdf"

LAND_COVERS = ["cropland", "forest", "grassland", "savanna"]
MODELS = ["DNN", "GBRT", "LR", "SVR"]
LAND_COLORS = {
    "cropland": ("#D18A2E", "#7A4700"),
    "forest": ("#3D8C59", "#15552A"),
    "grassland": ("#2D819D", "#154F61"),
    "savanna": ("#B65368", "#74263A"),
}


def load_data(path: Path) -> pd.DataFrame:
    """Load the paired columns and validate the expected workbook schema."""
    data = pd.read_excel(path, sheet_name="Sheet1", engine="openpyxl")
    expected = [
        f"{land}{model}_{suffix}"
        for land in LAND_COVERS
        for model in MODELS
        for suffix in (0, 1)
    ]
    missing = [column for column in expected if column not in data.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")
    return data.loc[:, expected]


def paired_values(
    data: pd.DataFrame, land: str, model: str
) -> tuple[np.ndarray, np.ndarray]:
    """Return finite observations shared by one _0/_1 column pair."""
    x = pd.to_numeric(data[f"{land}{model}_0"], errors="coerce").to_numpy(float)
    y = pd.to_numeric(data[f"{land}{model}_1"], errors="coerce").to_numpy(float)
    valid = np.isfinite(x) & np.isfinite(y)
    if valid.sum() < 2:
        raise ValueError(f"Insufficient paired values for {land} {model}")
    return x[valid], y[valid]


def common_limits(data: pd.DataFrame) -> tuple[float, float]:
    """Build one rounded axis range for direct comparison among all panels."""
    values = data.apply(pd.to_numeric, errors="coerce").to_numpy(float)
    finite = values[np.isfinite(values)]
    lower = 5.0 * np.floor(finite.min() / 5.0)
    upper = 5.0 * np.ceil(finite.max() / 5.0)
    if lower == upper:
        lower -= 5.0
        upper += 5.0
    return float(lower), float(upper)


def make_figure(data: pd.DataFrame):
    mpl.rcParams.update(
        {
            "font.family": "Arial",
            "font.size": 8.0,
            "axes.linewidth": 0.75,
            "axes.unicode_minus": True,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "savefig.facecolor": "white",
        }
    )

    axis_min, axis_max = common_limits(data)
    major_ticks = np.arange(
        np.ceil(axis_min / 20.0) * 20.0,
        axis_max + 0.1,
        20.0,
    )
    line_x = np.linspace(axis_min, axis_max, 250)

    fig, axes = uplt.subplots(
        nrows=4,
        ncols=4,
        figsize=(7.7, 8.15),
        share=False,
        left="0.70in",
        right="0.12in",
        bottom="0.50in",
        top="0.48in",
        wspace="0.08in",
        hspace="0.08in",
    )
    fig.patch.set_facecolor("white")

    letters = "abcdefghijklmnop"
    for row, land in enumerate(LAND_COVERS):
        point_color, fit_color = LAND_COLORS[land]
        for col, model in enumerate(MODELS):
            ax = axes[row * len(MODELS) + col]
            x, y = paired_values(data, land, model)
            slope, intercept = np.polyfit(x, y, deg=1)
            pearson_r = np.corrcoef(x, y)[0, 1]

            ax.grid(
                True,
                which="major",
                color="#E8E8E8",
                linewidth=0.48,
                zorder=0,
            )
            ax.plot(
                line_x,
                line_x,
                color="#777777",
                linewidth=0.85,
                linestyle=(0, (4, 3)),
                zorder=1,
            )
            ax.scatter(
                x,
                y,
                s=4.1,
                color=point_color,
                alpha=0.21,
                edgecolors="none",
                linewidths=0,
                rasterized=True,
                zorder=2,
            )
            ax.plot(
                line_x,
                slope * line_x + intercept,
                color=fit_color,
                linewidth=1.5,
                zorder=3,
            )

            ax.set_xlim(axis_min, axis_max)
            ax.set_ylim(axis_min, axis_max)
            ax.set_aspect("equal", adjustable="box")
            ax.set_xticks(major_ticks)
            ax.set_yticks(major_ticks)
            ax.xaxis.set_minor_locator(MultipleLocator(10))
            ax.yaxis.set_minor_locator(MultipleLocator(10))
            ax.tick_params(
                axis="both",
                which="major",
                direction="out",
                length=3.2,
                width=0.7,
                colors="#333333",
                labelsize=7.0,
                pad=2.0,
            )
            ax.tick_params(
                axis="both",
                which="minor",
                direction="out",
                length=1.8,
                width=0.55,
                colors="#555555",
            )
            ax.tick_params(labelbottom=row == len(LAND_COVERS) - 1)
            ax.tick_params(labelleft=col == 0)
            for spine in ax.spines.values():
                spine.set_color("#3A3A3A")
                spine.set_linewidth(0.75)

            if row == 0:
                ax.set_title(model, fontsize=10.0, fontweight="bold", pad=6.0)
            if row == len(LAND_COVERS) - 1:
                ax.set_xlabel("_0 value", fontsize=8.5, labelpad=4.0)

            ax.text(
                0.035,
                0.965,
                f"({letters[row * len(MODELS) + col]})",
                transform=ax.transAxes,
                ha="left",
                va="top",
                fontsize=8.2,
                fontweight="bold",
                color="#202020",
                zorder=5,
            )
            ax.text(
                0.965,
                0.045,
                f"Pearson r = {pearson_r:.3f}\nn = {len(x):,}",
                transform=ax.transAxes,
                ha="right",
                va="bottom",
                fontsize=7.1,
                linespacing=1.18,
                color="#202020",
                bbox={
                    "boxstyle": "square,pad=0.22",
                    "facecolor": "white",
                    "edgecolor": "none",
                    "alpha": 0.86,
                },
                zorder=5,
            )

    fig.canvas.draw()
    for row, land in enumerate(LAND_COVERS):
        position = axes[row * len(MODELS)].get_position()
        fig.text(
            0.022,
            (position.y0 + position.y1) / 2.0,
            f"{land.title()}  |  _1 value",
            rotation=90,
            ha="center",
            va="center",
            fontsize=8.7,
            fontweight="bold",
            color=LAND_COLORS[land][1],
        )

    fig.suptitle(
        "Correlation between _0 and _1 values",
        x=0.545,
        y=0.978,
        fontsize=12.0,
        fontweight="bold",
    )
    legend_handles = [
        Line2D([0], [0], color="#333333", linewidth=1.5, label="OLS fit"),
        Line2D(
            [0],
            [0],
            color="#777777",
            linewidth=0.85,
            linestyle=(0, (4, 3)),
            label="1:1 line",
        ),
    ]
    fig.legend(
        handles=legend_handles,
        loc="bottom",
        ncol=2,
        frameon=False,
        fontsize=8.0,
        handlelength=2.5,
        columnspacing=1.8,
    )
    return fig


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    data = load_data(DATA_PATH)
    figure = make_figure(data)
    figure.savefig(PDF_PATH, dpi=600, bbox_inches="tight", pad_inches=0.04)
    figure.savefig(PNG_PATH, dpi=600, bbox_inches="tight", pad_inches=0.04)
    uplt.close(figure)
    print(f"Saved: {PDF_PATH}")
    print(f"Saved: {PNG_PATH}")


if __name__ == "__main__":
    main()
