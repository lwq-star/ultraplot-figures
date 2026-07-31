"""Plot the global distribution of M5+ earthquakes in 2025 with UltraPlot."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import cartopy.crs as ccrs
import matplotlib.patheffects as path_effects
import matplotlib.pyplot as plt
import numpy as np
import ultraplot as uplt
from matplotlib.colors import LinearSegmentedColormap, PowerNorm
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from matplotlib.ticker import FixedFormatter, FixedLocator, MaxNLocator, NullLocator


SCRIPT_DIR = Path(__file__).resolve().parent
DATA_PATH = SCRIPT_DIR.parent / "data" / "usgs_earthquakes_2025_m5plus.geojson"
PNG_PATH = SCRIPT_DIR / "global_earthquakes_2025_m5plus.png"
PDF_PATH = SCRIPT_DIR / "global_earthquakes_2025_m5plus.pdf"

FIGURE_BG = "#F7F6F2"
TEXT = "#202A2D"
MUTED = "#687477"
GRID = "#C8D0CE"


def load_earthquakes(path: Path) -> dict[str, np.ndarray | list[str]]:
    """Read earthquake locations and attributes from a GeoJSON feature collection."""
    with path.open("r", encoding="utf-8") as stream:
        collection = json.load(stream)

    features = [
        feature
        for feature in collection.get("features", [])
        if (feature.get("properties") or {}).get("type") == "earthquake"
    ]
    if not features:
        raise ValueError(f"No earthquake features found in {path}")

    coordinates = np.asarray(
        [feature["geometry"]["coordinates"] for feature in features], dtype=float
    )
    magnitudes = np.asarray(
        [feature["properties"]["mag"] for feature in features], dtype=float
    )
    times = np.asarray(
        [feature["properties"]["time"] for feature in features], dtype=np.int64
    )
    places = [
        str(feature["properties"].get("place", "Unknown")) for feature in features
    ]

    valid = (
        np.isfinite(coordinates[:, 0])
        & np.isfinite(coordinates[:, 1])
        & np.isfinite(coordinates[:, 2])
        & np.isfinite(magnitudes)
    )
    if not np.all(valid):
        coordinates = coordinates[valid]
        magnitudes = magnitudes[valid]
        times = times[valid]
        places = [place for place, keep in zip(places, valid) if keep]

    return {
        "longitude": coordinates[:, 0],
        "latitude": coordinates[:, 1],
        "depth": np.clip(coordinates[:, 2], 0.0, None),
        "magnitude": magnitudes,
        "time": times,
        "place": places,
    }


def marker_area(magnitude: np.ndarray | float) -> np.ndarray | float:
    """Convert magnitude to scatter-marker area in points squared."""
    return 7.0 + 10.5 * np.square(np.asarray(magnitude) - 5.0)


def main() -> None:
    data = load_earthquakes(DATA_PATH)
    longitude = np.asarray(data["longitude"])
    latitude = np.asarray(data["latitude"])
    depth = np.asarray(data["depth"])
    magnitude = np.asarray(data["magnitude"])
    times = np.asarray(data["time"])
    places = list(data["place"])

    event_count = magnitude.size
    major_count = int(np.count_nonzero(magnitude >= 7.0))
    median_depth = float(np.median(depth))
    deepest = float(np.max(depth))

    depth_limit = max(650.0, float(np.ceil(deepest / 50.0) * 50.0))
    depth_cmap = LinearSegmentedColormap.from_list(
        "focal_depth",
        ["#F3D36A", "#E76F51", "#2A9D8F", "#3D6F8E", "#443A72"],
    )
    depth_norm = PowerNorm(gamma=0.55, vmin=0.0, vmax=depth_limit)

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9,
            "axes.titleweight": "bold",
            "axes.titlesize": 11,
            "axes.labelsize": 8.5,
            "axes.labelcolor": TEXT,
            "axes.edgecolor": GRID,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "text.color": TEXT,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )

    layout = [
        [1, 1, 1, 1, 2],
        [1, 1, 1, 1, 2],
        [1, 1, 1, 1, 3],
        [1, 1, 1, 1, 3],
    ]
    fig, axes = uplt.subplots(
        array=layout,
        proj={1: "robin"},
        width=13.8,
        height=7.7,
        wspace=5.2,
        hspace=3.0,
        share=False,
    )
    fig.patch.set_facecolor(FIGURE_BG)
    ax_map, ax_magnitude, ax_depth = axes

    ax_map.format(
        land=True,
        landcolor="#E3E7E3",
        ocean=True,
        oceancolor="#F1F5F5",
        coast=True,
        coastcolor="#7D8989",
        coastlinewidth=0.55,
        lonlines=60,
        latlines=30,
        gridcolor="#B8C4C3",
        gridlinewidth=0.42,
        gridalpha=0.65,
        labels=False,
    )

    # Draw small events first so the largest earthquakes remain visible.
    draw_order = np.argsort(magnitude)
    points = ax_map.scatter(
        longitude[draw_order],
        latitude[draw_order],
        c=depth[draw_order],
        s=marker_area(magnitude[draw_order]),
        cmap=depth_cmap,
        norm=depth_norm,
        transform=ccrs.PlateCarree(),
        edgecolors="#FFFFFF",
        linewidths=0.30,
        alpha=0.84,
        rasterized=True,
        zorder=4,
    )

    legend_magnitudes = [5.0, 6.0, 7.0, 8.0]
    size_handles = [
        Line2D(
            [0],
            [0],
            marker="o",
            linestyle="",
            markerfacecolor="#536F72",
            markeredgecolor="white",
            markeredgewidth=0.7,
            markersize=float(np.sqrt(marker_area(value))),
            label=f"M {value:.0f}",
        )
        for value in legend_magnitudes
    ]
    size_legend = ax_map.legend(
        handles=size_handles,
        title="Magnitude",
        loc="upper left",
        bbox_to_anchor=(0.015, 0.985),
        ncols=4,
        frameon=True,
        framealpha=0.94,
        facecolor="#FFFFFF",
        edgecolor="#D4DAD8",
        fontsize=7.5,
        title_fontsize=8,
        columnspacing=0.9,
        handletextpad=0.35,
        borderpad=0.55,
    )
    size_legend.set_zorder(10)

    depth_ticks = [0, 70, 300, int(depth_limit)]
    colorbar = ax_map.colorbar(
        points,
        loc="bottom",
        length=0.48,
        width=0.11,
        pad=0.40,
        ticks=depth_ticks,
        label="Focal depth (km)",
    )
    colorbar.ax.tick_params(labelsize=7.5, length=2.5, colors=MUTED)
    colorbar.ax.xaxis.label.set_size(8)
    colorbar.ax.xaxis.set_minor_locator(NullLocator())

    largest_index = int(np.argmax(magnitude))
    largest_date = datetime.fromtimestamp(
        times[largest_index] / 1000.0, tz=timezone.utc
    )
    largest_place = (
        places[largest_index].replace("2025 ", "").replace(" Earthquake", "")
    )
    annotation = (
        f"Largest event  M{magnitude[largest_index]:.1f}\n"
        f"{largest_place}\n"
        f"{largest_date:%d %b} | {depth[largest_index]:.0f} km deep"
    )
    note = ax_map.annotate(
        annotation,
        xy=(longitude[largest_index], latitude[largest_index]),
        xycoords=ccrs.PlateCarree()._as_mpl_transform(ax_map),
        xytext=(-112, -48),
        textcoords="offset points",
        ha="left",
        va="top",
        fontsize=7.6,
        linespacing=1.35,
        bbox={
            "boxstyle": "round,pad=0.45,rounding_size=0.12",
            "facecolor": "#FFFFFF",
            "edgecolor": "#B7C0BE",
            "linewidth": 0.65,
            "alpha": 0.96,
        },
        arrowprops={
            "arrowstyle": "-",
            "color": "#5E696A",
            "linewidth": 0.85,
            "shrinkA": 3,
            "shrinkB": 5,
            "connectionstyle": "arc3,rad=-0.12",
        },
        zorder=11,
    )
    note.set_path_effects([path_effects.withStroke(linewidth=0.5, foreground="white")])

    magnitude_bins = np.arange(5.0, 9.01, 0.25)
    magnitude_counts, magnitude_edges = np.histogram(magnitude, bins=magnitude_bins)
    magnitude_centers = (magnitude_edges[:-1] + magnitude_edges[1:]) / 2.0
    for center, count in zip(magnitude_centers, magnitude_counts):
        ax_magnitude.add_patch(
            Rectangle(
                (0.0, center - 0.10),
                float(count),
                0.20,
                facecolor="#426F75",
                edgecolor="none",
                alpha=0.93,
                zorder=3,
            )
        )
    ax_magnitude.set_ylim(4.92, 9.02)
    ax_magnitude.set_xlim(0, max(magnitude_counts) * 1.08)
    ax_magnitude.grid(axis="x", color=GRID, linewidth=0.55, alpha=0.7)
    ax_magnitude.set_axisbelow(True)
    ax_magnitude.format(
        title="Magnitude distribution",
        ylabel="Magnitude",
        facecolor=FIGURE_BG,
        ticklabelsize=7.5,
    )
    ax_magnitude.spines["top"].set_visible(False)
    ax_magnitude.spines["right"].set_visible(False)
    ax_magnitude.xaxis.set_major_locator(MaxNLocator(nbins=4, integer=True))
    ax_magnitude.xaxis.set_minor_locator(NullLocator())
    ax_magnitude.yaxis.set_major_locator(FixedLocator([5, 6, 7, 8, 9]))
    ax_magnitude.yaxis.set_minor_locator(NullLocator())
    ax_magnitude.text(
        0.97,
        0.94,
        f"M7.0+   {major_count:,}",
        transform=ax_magnitude.transAxes,
        ha="right",
        va="top",
        fontsize=8.2,
        fontweight="bold",
        color="#314F54",
    )

    depth_counts = np.asarray(
        [
            np.count_nonzero(depth < 70),
            np.count_nonzero((depth >= 70) & (depth <= 300)),
            np.count_nonzero(depth > 300),
        ]
    )
    depth_labels = ["Shallow\n<70 km", "Intermediate\n70-300 km", "Deep\n>300 km"]
    depth_samples = np.asarray([35.0, 180.0, min(500.0, depth_limit)])
    depth_colors = depth_cmap(depth_norm(depth_samples))
    y_positions = np.arange(3)
    for position, count, color in zip(y_positions, depth_counts, depth_colors):
        ax_depth.add_patch(
            Rectangle(
                (0.0, position - 0.28),
                float(count),
                0.56,
                facecolor=color,
                edgecolor="none",
                zorder=3,
            )
        )
    label_room = float(np.max(depth_counts)) * 1.27
    ax_depth.set_xlim(0, label_room)
    ax_depth.set_ylim(2.60, -0.60)
    ax_depth.grid(axis="x", color=GRID, linewidth=0.55, alpha=0.7)
    ax_depth.set_axisbelow(True)
    ax_depth.format(
        title="Depth classes",
        xlabel="Number of earthquakes",
        facecolor=FIGURE_BG,
        ticklabelsize=7.5,
    )
    ax_depth.spines["top"].set_visible(False)
    ax_depth.spines["right"].set_visible(False)
    ax_depth.xaxis.set_major_locator(MaxNLocator(nbins=4, integer=True))
    ax_depth.xaxis.set_minor_locator(NullLocator())
    ax_depth.yaxis.set_major_locator(FixedLocator(y_positions))
    ax_depth.yaxis.set_major_formatter(FixedFormatter(depth_labels))
    ax_depth.yaxis.set_minor_locator(NullLocator())
    ax_depth.tick_params(axis="y", pad=5)
    for position, count in zip(y_positions, depth_counts):
        percent = 100.0 * count / event_count
        ax_depth.text(
            count + label_room * 0.025,
            position,
            f"{count:,}\n{percent:.1f}%",
            ha="left",
            va="center",
            fontsize=7.5,
            fontweight="bold",
            color=TEXT,
            linespacing=1.15,
        )
    ax_depth.text(
        0.98,
        0.96,
        f"Median {median_depth:.0f} km | Deepest {deepest:.0f} km",
        transform=ax_depth.transAxes,
        ha="right",
        va="top",
        fontsize=7.4,
        color=MUTED,
    )

    fig.text(
        0.03,
        0.985,
        "Global Earthquakes of Magnitude 5.0+ | 2025",
        ha="left",
        va="top",
        fontsize=17,
        fontweight="bold",
        color=TEXT,
    )
    fig.text(
        0.03,
        0.923,
        (
            f"{event_count:,} earthquakes recorded worldwide | "
            f"M{magnitude.min():.1f}-M{magnitude.max():.1f} | "
            f"circle area shows magnitude, color shows focal depth"
        ),
        ha="left",
        va="top",
        fontsize=9.2,
        color=MUTED,
    )
    fig.text(
        0.03,
        0.018,
        "Data: USGS earthquake catalog GeoJSON | Depth classes: shallow <70 km, intermediate 70-300 km, deep >300 km",
        ha="left",
        va="bottom",
        fontsize=7.3,
        color=MUTED,
    )

    save_options = {
        "bbox_inches": "tight",
        "facecolor": FIGURE_BG,
        "edgecolor": "none",
    }
    fig.savefig(PNG_PATH, dpi=300, **save_options)
    fig.savefig(PDF_PATH, dpi=300, **save_options)
    plt.close(fig)

    print(f"Saved {PNG_PATH}")
    print(f"Saved {PDF_PATH}")
    print(
        f"Events: {event_count:,}; M7+: {major_count:,}; "
        f"magnitude range: {magnitude.min():.1f}-{magnitude.max():.1f}; "
        f"depth range: {depth.min():.1f}-{depth.max():.1f} km"
    )


if __name__ == "__main__":
    main()
