from __future__ import annotations

import json
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LogNorm
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter, ScalarFormatter
from PIL import Image


EXAMPLE_DIR = Path(__file__).resolve().parents[1]
INPUT_GEOJSON = EXAMPLE_DIR / "data" / "usgs_earthquakes_2025_m5plus.geojson"
OUTPUT_DIR = Path(__file__).resolve().parent
PDF_PATH = OUTPUT_DIR / "earthquakes_2025_m5plus.pdf"
TIFF_PATH = OUTPUT_DIR / "earthquakes_2025_m5plus_600dpi.tif"

FIGURE_WIDTH_MM = 183.0
FIGURE_HEIGHT_MM = 132.0
TIFF_DPI = 600

LAND_COLOR = "#f2f0e9"
OCEAN_COLOR = "#eaf2f5"
COAST_COLOR = "#707b7c"
TEXT_COLOR = "#20272b"
GRID_COLOR = "#b9c4c7"
MAG_COLOR = "#526f7a"
STRONG_MAG_COLOR = "#b9543e"
DEPTH_CMAP = mpl.colormaps["viridis_r"]


def configure_style() -> None:
    mpl.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 7.0,
            "axes.labelsize": 7.0,
            "axes.titlesize": 8.0,
            "axes.titleweight": "semibold",
            "axes.labelcolor": TEXT_COLOR,
            "axes.edgecolor": "#6f777a",
            "axes.linewidth": 0.6,
            "axes.facecolor": "white",
            "xtick.color": TEXT_COLOR,
            "ytick.color": TEXT_COLOR,
            "xtick.labelsize": 6.5,
            "ytick.labelsize": 6.5,
            "xtick.major.size": 2.8,
            "ytick.major.size": 2.8,
            "xtick.major.width": 0.55,
            "ytick.major.width": 0.55,
            "grid.color": GRID_COLOR,
            "grid.linewidth": 0.45,
            "grid.alpha": 0.65,
            "legend.fontsize": 6.0,
            "legend.title_fontsize": 6.2,
            "figure.facecolor": "white",
            "savefig.facecolor": "white",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def load_earthquakes(path: Path) -> tuple[dict[str, np.ndarray], dict[str, object]]:
    with path.open("r", encoding="utf-8") as stream:
        collection = json.load(stream)

    if collection.get("type") != "FeatureCollection":
        raise ValueError("Input is not a GeoJSON FeatureCollection.")

    features = collection.get("features", [])
    if not features:
        raise ValueError("Input FeatureCollection contains no features.")

    records: list[dict[str, object]] = []
    ids: list[str] = []
    type_counts: Counter[str] = Counter()

    for index, feature in enumerate(features):
        geometry = feature.get("geometry") or {}
        properties = feature.get("properties") or {}
        if geometry.get("type") != "Point":
            raise ValueError(f"Feature {index} is not a Point geometry.")
        coordinates = geometry.get("coordinates") or []
        if len(coordinates) < 3:
            raise ValueError(f"Feature {index} lacks longitude, latitude, or depth.")

        event_id = feature.get("id")
        event_type = properties.get("type")
        magnitude = properties.get("mag")
        timestamp_ms = properties.get("time")
        if event_id is None or event_type is None or magnitude is None or timestamp_ms is None:
            raise ValueError(f"Feature {index} lacks a required event property.")

        lon, lat, depth = map(float, coordinates[:3])
        magnitude = float(magnitude)
        values = np.asarray([lon, lat, depth, magnitude, float(timestamp_ms)])
        if not np.all(np.isfinite(values)):
            raise ValueError(f"Feature {index} contains non-finite values.")
        if not (-180.0 <= lon <= 180.0 and -90.0 <= lat <= 90.0):
            raise ValueError(f"Feature {index} has invalid geographic coordinates.")

        ids.append(str(event_id))
        type_counts[str(event_type)] += 1
        records.append(
            {
                "id": str(event_id),
                "type": str(event_type),
                "lon": lon,
                "lat": lat,
                "depth": depth,
                "magnitude": magnitude,
                "time": datetime.fromtimestamp(float(timestamp_ms) / 1000.0, tz=timezone.utc),
                "place": str(properties.get("place", "")),
                "status": str(properties.get("status", "")),
                "mag_type": str(properties.get("magType", "")),
            }
        )

    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate event IDs are present in the input.")

    earthquakes = [record for record in records if record["type"] == "earthquake"]
    if not earthquakes:
        raise ValueError("No records classified as earthquakes were found.")

    plotted = {
        "id": np.asarray([record["id"] for record in earthquakes], dtype=object),
        "lon": np.asarray([record["lon"] for record in earthquakes], dtype=float),
        "lat": np.asarray([record["lat"] for record in earthquakes], dtype=float),
        "depth": np.asarray([record["depth"] for record in earthquakes], dtype=float),
        "magnitude": np.asarray([record["magnitude"] for record in earthquakes], dtype=float),
        "time": np.asarray([record["time"] for record in earthquakes], dtype=object),
        "place": np.asarray([record["place"] for record in earthquakes], dtype=object),
        "status": np.asarray([record["status"] for record in earthquakes], dtype=object),
        "mag_type": np.asarray([record["mag_type"] for record in earthquakes], dtype=object),
    }

    if np.min(plotted["magnitude"]) < 5.0:
        raise ValueError("At least one plotted earthquake has magnitude below 5.0.")
    if np.min(plotted["depth"]) <= 0.0:
        raise ValueError("Logarithmic depth colors require positive earthquake depths.")
    if any(moment.year != 2025 for moment in plotted["time"]):
        raise ValueError("At least one plotted earthquake lies outside calendar year 2025 UTC.")

    excluded_counts = type_counts.copy()
    excluded_counts.subtract({"earthquake": len(earthquakes)})
    excluded_counts = Counter({key: value for key, value in excluded_counts.items() if value})
    info: dict[str, object] = {
        "input_count": len(records),
        "plotted_count": len(earthquakes),
        "excluded_counts": dict(excluded_counts),
        "type_counts": dict(type_counts),
        "all_reviewed": bool(np.all(plotted["status"] == "reviewed")),
        "magnitude_types": dict(Counter(plotted["mag_type"])),
    }
    return plotted, info


def marker_area(magnitude: np.ndarray | float) -> np.ndarray:
    values = np.asarray(magnitude, dtype=float)
    return 9.0 + 8.5 * np.square(values - 5.0)


def panel_label(ax: mpl.axes.Axes, label: str, x: float = -0.08) -> None:
    ax.text(
        x,
        1.04,
        label,
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=8.5,
        fontweight="bold",
        color=TEXT_COLOR,
        clip_on=False,
    )


def add_map_panel(
    fig: mpl.figure.Figure,
    spec: mpl.gridspec.SubplotSpec,
    data: dict[str, np.ndarray],
) -> mpl.axes.Axes:
    projection = ccrs.Robinson(central_longitude=0)
    plate_carree = ccrs.PlateCarree()
    ax = fig.add_subplot(spec, projection=projection)
    ax.set_global()
    ax.add_feature(cfeature.OCEAN.with_scale("110m"), facecolor=OCEAN_COLOR, zorder=0)
    ax.add_feature(cfeature.LAND.with_scale("110m"), facecolor=LAND_COLOR, zorder=0.2)
    ax.coastlines(resolution="110m", color=COAST_COLOR, linewidth=0.42, zorder=0.4)
    ax.gridlines(
        crs=plate_carree,
        xlocs=np.arange(-180, 181, 60),
        ylocs=np.arange(-60, 61, 30),
        color=GRID_COLOR,
        linewidth=0.42,
        linestyle=(0, (1.5, 2.0)),
        alpha=0.75,
        zorder=0.3,
    )
    ax.spines["geo"].set_edgecolor("#6f777a")
    ax.spines["geo"].set_linewidth(0.65)

    order = np.argsort(data["magnitude"], kind="stable")
    depth_norm = LogNorm(vmin=3.0, vmax=700.0)
    scatter = ax.scatter(
        data["lon"][order],
        data["lat"][order],
        s=marker_area(data["magnitude"][order]),
        c=data["depth"][order],
        cmap=DEPTH_CMAP,
        norm=depth_norm,
        transform=plate_carree,
        alpha=0.82,
        linewidths=0.24,
        edgecolors="#182126",
        zorder=2.0,
    )

    ax.text(
        0.018,
        0.952,
        "a",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=8.5,
        fontweight="bold",
        color=TEXT_COLOR,
        bbox={"boxstyle": "square,pad=0.15", "facecolor": "white", "edgecolor": "none", "alpha": 0.88},
        zorder=4,
    )
    ax.text(
        0.019,
        0.886,
        f"n = {len(data['magnitude']):,}",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=6.5,
        color=TEXT_COLOR,
        bbox={"boxstyle": "square,pad=0.28", "facecolor": "white", "edgecolor": "none", "alpha": 0.88},
        zorder=4,
    )

    legend_magnitudes = [5.0, 6.0, 7.0, 8.5]
    handles = [
        Line2D(
            [],
            [],
            linestyle="none",
            marker="o",
            markersize=float(np.sqrt(marker_area(value))),
            markerfacecolor="#f5f5f5",
            markeredgecolor="#1c2529",
            markeredgewidth=0.45,
            label=f"{value:g}",
        )
        for value in legend_magnitudes
    ]
    legend = ax.legend(
        handles=handles,
        title="Magnitude",
        loc="lower left",
        bbox_to_anchor=(0.014, 0.018),
        ncol=4,
        frameon=True,
        fancybox=False,
        framealpha=0.9,
        borderpad=0.45,
        handletextpad=0.35,
        columnspacing=0.75,
        labelspacing=0.4,
    )
    legend.get_frame().set_edgecolor("#a5adaf")
    legend.get_frame().set_linewidth(0.45)

    color_ax = ax.inset_axes([0.625, 0.045, 0.315, 0.031])
    colorbar = fig.colorbar(scatter, cax=color_ax, orientation="horizontal")
    colorbar.set_ticks([3, 10, 30, 100, 300, 700])
    colorbar.ax.xaxis.set_major_formatter(ScalarFormatter())
    colorbar.ax.tick_params(axis="x", which="major", length=2.0, width=0.45, pad=1.0, labelsize=5.3)
    colorbar.ax.tick_params(axis="x", which="minor", length=0)
    colorbar.ax.xaxis.set_label_position("top")
    colorbar.set_label("Hypocentral depth (km; log color scale)", fontsize=5.8, labelpad=1.2)
    colorbar.outline.set_linewidth(0.45)
    colorbar.outline.set_edgecolor("#70787b")
    color_ax.set_facecolor("white")

    largest = int(np.argmax(data["magnitude"]))
    annotation_transform = plate_carree._as_mpl_transform(ax)
    largest_date = data["time"][largest].strftime("%d %b")
    ax.annotate(
        f"M {data['magnitude'][largest]:.1f}, {data['depth'][largest]:g} km\nKamchatka, {largest_date}",
        xy=(data["lon"][largest], data["lat"][largest]),
        xycoords=annotation_transform,
        xytext=(-15, -22),
        textcoords="offset points",
        ha="right",
        va="top",
        fontsize=5.7,
        linespacing=1.15,
        color=TEXT_COLOR,
        arrowprops={"arrowstyle": "-", "color": "#363f43", "linewidth": 0.55, "shrinkA": 2, "shrinkB": 3},
        bbox={"boxstyle": "square,pad=0.22", "facecolor": "white", "edgecolor": "#899194", "linewidth": 0.4, "alpha": 0.93},
        zorder=5,
    )
    return ax


def add_magnitude_panel(
    fig: mpl.figure.Figure,
    spec: mpl.gridspec.SubplotSpec,
    magnitudes: np.ndarray,
) -> mpl.axes.Axes:
    ax = fig.add_subplot(spec)
    bins = np.arange(5.0, 9.0001, 0.25)
    counts, edges = np.histogram(magnitudes, bins=bins)
    centers = 0.5 * (edges[:-1] + edges[1:])
    colors = [STRONG_MAG_COLOR if center >= 7.0 else MAG_COLOR for center in centers]
    ax.bar(
        edges[:-1],
        counts,
        width=np.diff(edges) * 0.9,
        align="edge",
        color=colors,
        edgecolor="white",
        linewidth=0.3,
        zorder=2,
    )
    ax.set_yscale("log")
    ax.set_xlim(4.95, 9.05)
    ax.set_ylim(0.8, max(counts) * 1.8)
    ax.set_xticks([5, 6, 7, 8, 9])
    ax.set_yticks([1, 10, 100, 1000])
    ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:g}"))
    ax.grid(axis="y", which="major", zorder=0)
    ax.set_axisbelow(True)
    ax.set_title("Magnitude distribution", loc="left", pad=4.0)
    ax.set_xlabel("Reported magnitude")
    ax.set_ylabel("Events per 0.25 M (log scale)")
    panel_label(ax, "b")
    strong_count = int(np.count_nonzero(magnitudes >= 7.0))
    ax.text(
        0.98,
        0.93,
        f"M >= 7: {strong_count}",
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=6.2,
        color=STRONG_MAG_COLOR,
        fontweight="semibold",
    )
    ax.spines[["top", "right"]].set_visible(False)
    return ax


def add_depth_panel(
    fig: mpl.figure.Figure,
    spec: mpl.gridspec.SubplotSpec,
    depths: np.ndarray,
) -> mpl.axes.Axes:
    ax = fig.add_subplot(spec)
    edges = np.asarray([0.0, 35.0, 70.0, 300.0, 700.0001])
    labels = ["0-34", "35-69", "70-299", "300-700"]
    counts, _ = np.histogram(depths, bins=edges)
    percentages = counts / len(depths) * 100.0
    color_values = np.asarray([10.0, 50.0, 150.0, 450.0])
    colors = DEPTH_CMAP(LogNorm(vmin=3.0, vmax=700.0)(color_values))
    positions = np.arange(len(labels))
    ax.barh(
        positions,
        percentages,
        height=0.66,
        color=colors,
        edgecolor="#334045",
        linewidth=0.35,
        zorder=2,
    )
    ax.set_yticks(positions, labels)
    ax.invert_yaxis()
    ax.set_xlim(0, 84)
    ax.set_xticks([0, 20, 40, 60, 80])
    ax.grid(axis="x", which="major", zorder=0)
    ax.set_axisbelow(True)
    ax.set_title("Depth distribution", loc="left", pad=4.0)
    ax.set_xlabel("Share of plotted earthquakes (%)")
    ax.set_ylabel("Depth range (km)")
    panel_label(ax, "c")
    for position, count, percentage in zip(positions, counts, percentages, strict=True):
        ax.text(
            percentage + 1.0,
            position,
            f"{count:,} ({percentage:.1f}%)",
            va="center",
            ha="left",
            fontsize=6.0,
            color=TEXT_COLOR,
        )
    ax.spines[["top", "right"]].set_visible(False)
    return ax


def create_figure(data: dict[str, np.ndarray], info: dict[str, object]) -> mpl.figure.Figure:
    width_in = FIGURE_WIDTH_MM / 25.4
    height_in = FIGURE_HEIGHT_MM / 25.4
    fig = plt.figure(figsize=(width_in, height_in))
    grid = fig.add_gridspec(
        2,
        2,
        height_ratios=[3.25, 1.12],
        left=0.078,
        right=0.985,
        top=0.885,
        bottom=0.105,
        hspace=0.34,
        wspace=0.27,
    )
    add_map_panel(fig, grid[0, :], data)
    add_magnitude_panel(fig, grid[1, 0], data["magnitude"])
    add_depth_panel(fig, grid[1, 1], data["depth"])

    fig.text(
        0.078,
        0.965,
        "Global M >= 5 earthquakes in 2025",
        ha="left",
        va="top",
        fontsize=12.0,
        fontweight="bold",
        color=TEXT_COLOR,
    )
    fig.text(
        0.078,
        0.923,
        (
            f"{info['plotted_count']:,} reviewed events; "
            f"M {np.min(data['magnitude']):.1f}-{np.max(data['magnitude']):.1f}; "
            f"depth {np.min(data['depth']):g}-{np.max(data['depth']):g} km"
        ),
        ha="left",
        va="top",
        fontsize=7.0,
        color="#4a555a",
    )

    start = min(data["time"]).strftime("%d %b")
    end = max(data["time"]).strftime("%d %b %Y UTC")
    footer = (
        f"Data span: {start}-{end}. One supplied landslide record was excluded.\n"
        "Magnitudes are reported values (mixed magnitude types); depths are GeoJSON coordinate values."
    )
    fig.text(
        0.078,
        0.014,
        footer,
        ha="left",
        va="bottom",
        fontsize=5.4,
        linespacing=1.18,
        color="#596368",
    )
    return fig


def print_summary(data: dict[str, np.ndarray], info: dict[str, object]) -> None:
    print(f"Input: {INPUT_GEOJSON.relative_to(EXAMPLE_DIR).as_posix()}")
    print(f"Input features: {info['input_count']}")
    print(f"Type counts: {info['type_counts']}")
    print(f"Excluded counts: {info['excluded_counts']}")
    print(f"Plotted earthquakes: {info['plotted_count']}")
    print(f"All plotted events reviewed: {info['all_reviewed']}")
    print(f"Magnitude types: {info['magnitude_types']}")
    print(f"UTC range: {min(data['time']).isoformat()} to {max(data['time']).isoformat()}")
    print(f"Longitude range: {np.min(data['lon']):.4f} to {np.max(data['lon']):.4f}")
    print(f"Latitude range: {np.min(data['lat']):.4f} to {np.max(data['lat']):.4f}")
    print(f"Magnitude range: {np.min(data['magnitude']):.1f} to {np.max(data['magnitude']):.1f}")
    print(f"Depth range (km): {np.min(data['depth']):g} to {np.max(data['depth']):g}")
    print(f"M >= 7 count: {np.count_nonzero(data['magnitude'] >= 7.0)}")
    print(f"Figure size (mm): {FIGURE_WIDTH_MM:g} x {FIGURE_HEIGHT_MM:g}")
    print(f"PDF: {PDF_PATH.relative_to(EXAMPLE_DIR).as_posix()}")
    print(f"TIFF: {TIFF_PATH.relative_to(EXAMPLE_DIR).as_posix()}")
    print(f"TIFF settings: RGB, {TIFF_DPI} dpi, LZW compression")


def main() -> None:
    configure_style()
    data, info = load_earthquakes(INPUT_GEOJSON)
    figure = create_figure(data, info)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    figure.savefig(
        PDF_PATH,
        format="pdf",
        dpi=TIFF_DPI,
        metadata={
            "Title": "Global M >= 5 earthquakes in 2025",
            "Subject": "Spatial distribution, magnitude, and depth of supplied 2025 earthquake records",
            "Creator": "Matplotlib and Cartopy",
        },
    )
    with tempfile.TemporaryDirectory(prefix="earthquake_figure_") as temp_dir:
        rgba_path = Path(temp_dir) / "render_rgba.tif"
        figure.savefig(
            rgba_path,
            format="tiff",
            dpi=TIFF_DPI,
            pil_kwargs={"compression": "tiff_lzw"},
        )
        with Image.open(rgba_path) as rendered:
            rendered.convert("RGB").save(
                TIFF_PATH,
                format="TIFF",
                compression="tiff_lzw",
                dpi=(TIFF_DPI, TIFF_DPI),
            )
    plt.close(figure)
    print_summary(data, info)


if __name__ == "__main__":
    main()
