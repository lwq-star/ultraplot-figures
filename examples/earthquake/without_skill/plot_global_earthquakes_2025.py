#!/usr/bin/env python
"""Plot the global distribution of reviewed M5+ earthquakes in 2025."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib as mpl
import numpy as np
import ultraplot as uplt
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.lines import Line2D


OUTPUT_DIR = Path(__file__).resolve().parent
INPUT_GEOJSON = OUTPUT_DIR.parent / "data" / "usgs_earthquakes_2025_m5plus.geojson"
PNG_PATH = OUTPUT_DIR / "global_earthquakes_2025_m5plus.png"
PDF_PATH = OUTPUT_DIR / "global_earthquakes_2025_m5plus.pdf"

DEPTH_EDGES = np.array([0.0, 20.0, 70.0, 150.0, 300.0, 500.0, 650.0])
DEPTH_COLORS = [
    "#FDE725",
    "#A0DA39",
    "#4AC16D",
    "#1FA187",
    "#277F8E",
    "#365C8D",
]


def load_events(path: Path) -> dict[str, np.ndarray | list[str]]:
    """Load and validate the fields needed from the USGS GeoJSON."""
    with path.open("r", encoding="utf-8") as stream:
        collection = json.load(stream)

    if collection.get("type") != "FeatureCollection":
        raise ValueError("Expected a GeoJSON FeatureCollection.")
    features = collection.get("features", [])
    if not features:
        raise ValueError("The GeoJSON contains no features.")

    longitudes: list[float] = []
    latitudes: list[float] = []
    depths: list[float] = []
    magnitudes: list[float] = []
    times: list[int] = []
    places: list[str] = []

    for index, feature in enumerate(features):
        geometry = feature.get("geometry") or {}
        properties = feature.get("properties") or {}
        coordinates = geometry.get("coordinates") or []
        if geometry.get("type") != "Point" or len(coordinates) < 3:
            raise ValueError(f"Feature {index} is not a 3D Point geometry.")
        if properties.get("mag") is None or properties.get("time") is None:
            raise ValueError(f"Feature {index} lacks magnitude or event time.")

        longitudes.append(float(coordinates[0]))
        latitudes.append(float(coordinates[1]))
        depths.append(float(coordinates[2]))
        magnitudes.append(float(properties["mag"]))
        times.append(int(properties["time"]))
        places.append(str(properties.get("place") or "Unnamed location"))

    arrays: dict[str, np.ndarray | list[str]] = {
        "longitude": np.asarray(longitudes),
        "latitude": np.asarray(latitudes),
        "depth": np.asarray(depths),
        "magnitude": np.asarray(magnitudes),
        "time": np.asarray(times, dtype=np.int64),
        "place": places,
    }

    years = {
        datetime.fromtimestamp(value / 1000, tz=timezone.utc).year
        for value in arrays["time"]
    }
    if years != {2025}:
        raise ValueError(f"Expected only 2025 events, found years {sorted(years)}.")
    if np.any(~np.isfinite(arrays["magnitude"])) or np.any(
        ~np.isfinite(arrays["depth"])
    ):
        raise ValueError("Magnitude and depth must be finite for every event.")
    return arrays


def marker_area(magnitude: np.ndarray | float) -> np.ndarray | float:
    """Return marker area in points squared; area grows with magnitude."""
    return 9.0 * np.power(2.4, np.asarray(magnitude) - 5.0)


def make_figure(events: dict[str, np.ndarray | list[str]]) -> mpl.figure.Figure:
    longitude = np.asarray(events["longitude"])
    latitude = np.asarray(events["latitude"])
    depth = np.asarray(events["depth"])
    magnitude = np.asarray(events["magnitude"])
    event_times = np.asarray(events["time"])
    places = events["place"]
    count = magnitude.size

    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "DejaVu Sans"],
            "font.size": 8.5,
            "axes.titleweight": "semibold",
            "figure.facecolor": "white",
            "savefig.facecolor": "white",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )

    fig, axes = uplt.subplots(proj="robin", figsize=(9.0, 6.0), tight=False)
    ax = axes[0]
    ax.set_position([0.02, 0.205, 0.96, 0.69])
    ax.set_global()
    ocean_color = "#DFEAF0"
    land_color = "#F1F0EC"
    ax.set_facecolor(ocean_color)
    ax.add_feature(
        cfeature.LAND.with_scale("110m"),
        facecolor=land_color,
        edgecolor="none",
        zorder=0,
    )
    ax.add_feature(
        cfeature.LAKES.with_scale("110m"),
        facecolor=ocean_color,
        edgecolor="none",
        zorder=0.2,
    )
    gridlines = ax.gridlines(
        crs=ccrs.PlateCarree(),
        draw_labels=False,
        xlocs=np.arange(-180, 181, 60),
        ylocs=np.arange(-60, 61, 30),
        linewidth=0.35,
        color="#87939A",
        alpha=0.52,
        linestyle=(0, (2, 3)),
        zorder=0.5,
    )
    gridlines.x_inline = False
    gridlines.y_inline = False
    ax.coastlines(
        resolution="110m", color="#56636A", linewidth=0.48, zorder=1.2
    )
    if "geo" in ax.spines:
        ax.spines["geo"].set_edgecolor("#59666D")
        ax.spines["geo"].set_linewidth(0.65)

    depth_cmap = ListedColormap(DEPTH_COLORS, name="depth_viridis")
    depth_norm = BoundaryNorm(DEPTH_EDGES, depth_cmap.N, clip=True)
    draw_order = np.argsort(magnitude, kind="stable")

    scatter = ax.scatter(
        longitude[draw_order],
        latitude[draw_order],
        c=depth[draw_order],
        s=marker_area(magnitude[draw_order]),
        cmap=depth_cmap,
        norm=depth_norm,
        transform=ccrs.PlateCarree(),
        marker="o",
        edgecolors="#F8FAFB",
        linewidths=0.24,
        alpha=0.82,
        rasterized=True,
        zorder=2,
    )

    large = magnitude >= 7.0
    ax.scatter(
        longitude[large],
        latitude[large],
        c=depth[large],
        s=marker_area(magnitude[large]),
        cmap=depth_cmap,
        norm=depth_norm,
        transform=ccrs.PlateCarree(),
        marker="o",
        edgecolors="#20272B",
        linewidths=0.62,
        alpha=0.97,
        rasterized=True,
        zorder=3,
    )

    largest = int(np.argmax(magnitude))
    largest_xy_transform = ccrs.PlateCarree()._as_mpl_transform(ax)
    largest_date = datetime.fromtimestamp(
        event_times[largest] / 1000, tz=timezone.utc
    ).strftime("%d %b")
    largest_place = str(places[largest]).replace("2025 ", "")
    if " Earthquake" in largest_place:
        largest_place = largest_place.replace(" Earthquake", "")
    ax.annotate(
        f"Largest event  M{magnitude[largest]:.1f}\n{largest_place}  |  {largest_date}",
        xy=(longitude[largest], latitude[largest]),
        xycoords=largest_xy_transform,
        xytext=(-74, -7),
        textcoords="offset points",
        ha="right",
        va="center",
        fontsize=7.4,
        color="#20272B",
        linespacing=1.25,
        bbox={
            "boxstyle": "round,pad=0.24,rounding_size=0.12",
            "facecolor": "white",
            "edgecolor": "#4D5960",
            "linewidth": 0.45,
            "alpha": 0.93,
        },
        arrowprops={
            "arrowstyle": "-",
            "color": "#30383D",
            "linewidth": 0.65,
            "shrinkA": 2,
            "shrinkB": 3,
        },
        zorder=5,
    )

    fig.text(
        0.5,
        0.965,
        "Global distribution of M5+ earthquakes in 2025",
        ha="center",
        va="top",
        fontsize=17.0,
        fontweight="semibold",
        color="#172126",
    )
    fig.text(
        0.5,
        0.921,
        f"All {count:,} reviewed events  |  circle area: magnitude  |  color: hypocentral depth",
        ha="center",
        va="top",
        fontsize=8.8,
        color="#4D5A61",
    )

    magnitude_levels = [5.0, 6.0, 7.0, 8.0]
    magnitude_handles = [
        Line2D(
            [0],
            [0],
            linestyle="none",
            marker="o",
            markersize=float(np.sqrt(marker_area(value))),
            markerfacecolor="#436C82",
            markeredgecolor="white",
            markeredgewidth=0.45,
            alpha=0.9,
        )
        for value in magnitude_levels
    ]
    legend = mpl.figure.Figure.legend(
        fig,
        magnitude_handles,
        [f"M{value:.0f}" for value in magnitude_levels],
        title="MAGNITUDE",
        loc="center left",
        bbox_to_anchor=(0.052, 0.142),
        ncol=4,
        frameon=False,
        handletextpad=0.45,
        columnspacing=1.15,
        borderaxespad=0,
        fontsize=7.7,
        title_fontsize=7.2,
    )
    legend._legend_box.align = "left"

    colorbar_axis = fig.add_axes([0.56, 0.137, 0.385, 0.021])
    colorbar = mpl.figure.Figure.colorbar(
        fig,
        scatter,
        cax=colorbar_axis,
        orientation="horizontal",
        boundaries=DEPTH_EDGES,
        spacing="uniform",
        ticks=(DEPTH_EDGES[:-1] + DEPTH_EDGES[1:]) / 2,
    )
    colorbar.ax.set_xticklabels(
        ["0-20", "20-70", "70-150", "150-300", "300-500", "500-650"]
    )
    colorbar.ax.tick_params(length=0, pad=2.0, labelsize=6.9, colors="#3F4B51")
    colorbar.outline.set_linewidth(0.45)
    colorbar.outline.set_edgecolor("#59666D")
    colorbar.ax.set_title(
        "HYPOCENTRAL DEPTH (KM)",
        loc="left",
        fontsize=7.2,
        color="#303A3F",
        pad=5.2,
    )

    shallow = np.count_nonzero(depth < 70.0)
    intermediate = np.count_nonzero((depth >= 70.0) & (depth < 300.0))
    deep = np.count_nonzero(depth >= 300.0)
    m5_band = np.count_nonzero((magnitude >= 5.0) & (magnitude < 6.0))
    m6_plus = np.count_nonzero(magnitude >= 6.0)
    m7_plus = np.count_nonzero(magnitude >= 7.0)

    fig.add_artist(
        mpl.lines.Line2D(
            [0.052, 0.948],
            [0.091, 0.091],
            transform=fig.transFigure,
            color="#C8D0D4",
            linewidth=0.55,
        )
    )
    fig.text(
        0.052,
        0.067,
        "DEPTH PROFILE",
        ha="left",
        va="center",
        fontsize=6.9,
        fontweight="bold",
        color="#425058",
    )
    fig.text(
        0.158,
        0.067,
        (
            f"{100 * shallow / count:.1f}% shallow (<70 km)   "
            f"{100 * intermediate / count:.1f}% intermediate (70-300 km)   "
            f"{100 * deep / count:.1f}% deep (>300 km)"
        ),
        ha="left",
        va="center",
        fontsize=7.3,
        color="#344149",
    )
    fig.text(
        0.052,
        0.039,
        "MAGNITUDE PROFILE",
        ha="left",
        va="center",
        fontsize=6.9,
        fontweight="bold",
        color="#425058",
    )
    fig.text(
        0.181,
        0.039,
        (
            f"{100 * m5_band / count:.1f}% M5.0-5.9   "
            f"{m6_plus:,} M6+ events   {m7_plus:,} M7+ events   "
            f"largest M{magnitude[largest]:.1f}"
        ),
        ha="left",
        va="center",
        fontsize=7.3,
        color="#344149",
    )
    start_date = datetime.fromtimestamp(event_times.min() / 1000, tz=timezone.utc)
    end_date = datetime.fromtimestamp(event_times.max() / 1000, tz=timezone.utc)
    fig.text(
        0.948,
        0.017,
        (
            f"USGS GeoJSON  |  {start_date:%d %b}-{end_date:%d %b %Y} UTC  |  "
            "depth from point geometry"
        ),
        ha="right",
        va="center",
        fontsize=6.3,
        color="#69767C",
    )
    return fig


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    events = load_events(INPUT_GEOJSON)
    figure = make_figure(events)
    figure.savefig(
        PNG_PATH,
        dpi=300,
        facecolor="white",
        edgecolor="none",
    )
    figure.savefig(
        PDF_PATH,
        dpi=300,
        facecolor="white",
        edgecolor="none",
        metadata={
            "Title": "Global distribution of M5+ earthquakes in 2025",
            "Subject": "Magnitude and hypocentral depth of reviewed USGS events",
            "Author": "Generated with UltraPlot",
        },
    )
    uplt.close(figure)

    magnitude = np.asarray(events["magnitude"])
    depth = np.asarray(events["depth"])
    print(f"Events: {magnitude.size:,}")
    print(f"Magnitude range: {magnitude.min():.1f}-{magnitude.max():.1f}")
    print(f"Depth range: {depth.min():.1f}-{depth.max():.1f} km")
    print(f"PNG: {PNG_PATH}")
    print(f"PDF: {PDF_PATH}")


if __name__ == "__main__":
    main()
