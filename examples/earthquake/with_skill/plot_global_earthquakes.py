from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import cartopy.crs as ccrs
import matplotlib as mpl
import numpy as np
import ultraplot as uplt
from matplotlib.lines import Line2D


EXPORT_DPI = 1000
YEAR = 2025
ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = ROOT / "data" / "usgs_earthquakes_2025_m5plus.geojson"
OUTPUT_STEM = Path(__file__).resolve().parent / "global_earthquakes_2025_m5plus"


def load_earthquakes(path: Path) -> tuple[np.ndarray, ...]:
    if not path.is_file():
        raise FileNotFoundError(f"Input GeoJSON not found: {path}")

    collection = json.loads(path.read_text(encoding="utf-8"))
    if collection.get("type") != "FeatureCollection":
        raise ValueError("Expected a GeoJSON FeatureCollection.")

    rows = []
    for index, feature in enumerate(collection.get("features", []), start=1):
        geometry = feature.get("geometry") or {}
        properties = feature.get("properties") or {}
        coordinates = geometry.get("coordinates") or []
        if properties.get("type") != "earthquake":
            continue
        if geometry.get("type") != "Point" or len(coordinates) < 3:
            raise ValueError(f"Feature {index} is not a 3D GeoJSON Point.")
        if properties.get("mag") is None or properties.get("time") is None:
            raise ValueError(f"Feature {index} lacks magnitude or origin time.")
        rows.append((*coordinates[:3], properties["mag"], properties["time"]))

    if not rows:
        raise ValueError("The GeoJSON contains no earthquake features.")

    values = np.asarray(rows, dtype=float)
    if not np.isfinite(values).all():
        raise ValueError(
            "Longitude, latitude, depth, magnitude, and time must be finite."
        )

    longitude, latitude, depth_km, magnitude, time_ms = values.T
    if np.any((longitude < -180) | (longitude > 180)):
        raise ValueError("Longitude lies outside the EPSG:4326 range.")
    if np.any((latitude < -90) | (latitude > 90)):
        raise ValueError("Latitude lies outside the EPSG:4326 range.")
    if np.any(depth_km < 0):
        raise ValueError("Hypocentral depth must be non-negative.")
    if np.any(magnitude < 5):
        raise ValueError("The M5+ dataset contains a magnitude below 5.")

    # RFC 7946 GeoJSON positions are longitude/latitude in WGS84; the third
    # coordinate is interpreted here as USGS hypocentral depth in kilometres.
    years = {
        datetime.fromtimestamp(timestamp / 1000, tz=UTC).year for timestamp in time_ms
    }
    if years != {YEAR}:
        raise ValueError(f"Expected only {YEAR} origin times, found {sorted(years)}.")

    return longitude, latitude, depth_km, magnitude


def marker_area(magnitude: np.ndarray | float) -> np.ndarray | float:
    """Return marker area in points squared for the magnitude size encoding."""
    return 7.0 * np.power(2.0, np.asarray(magnitude) - 5.0)


def main() -> None:
    longitude, latitude, depth_km, magnitude = load_earthquakes(INPUT_PATH)
    draw_order = np.argsort(magnitude, kind="stable")

    magnitude_masks = (
        (magnitude >= 5) & (magnitude < 6),
        (magnitude >= 6) & (magnitude < 7),
        (magnitude >= 7) & (magnitude < 8),
        magnitude >= 8,
    )
    magnitude_counts = np.array([mask.sum() for mask in magnitude_masks])
    depth_masks = (
        depth_km < 70,
        (depth_km >= 70) & (depth_km < 300),
        depth_km >= 300,
    )
    depth_counts = np.array([mask.sum() for mask in depth_masks])

    style = {
        "font.size": 8.5,
        "axes.labelsize": 8.5,
        "xtick.labelsize": 7.5,
        "ytick.labelsize": 7.5,
        "legend.fontsize": 7.5,
    }
    with uplt.rc.context(style):
        fig, axes = uplt.subplots(
            [[1, 1], [2, 3]],
            proj={1: "pcarree"},
            journal="nat2",
            refnum=1,
            hratios=(2.6, 1.0),
            share=False,
            span=False,
            abc="a.",
            abcloc="ul",
        )
        map_ax, magnitude_ax, depth_ax = axes

        map_ax.format(
            lonlim=(-180, 180),
            latlim=(-90, 90),
            lonlocator=60,
            latlocator=30,
            lonlabels="b",
            latlabels="l",
            grid=True,
            coast=True,
            land=True,
            ocean=True,
            landcolor="#F2F0E9",
            oceancolor="#EAF2F4",
            coastcolor="#66645F",
            coastlinewidth=0.5,
        )

        points = map_ax.scatter(
            longitude[draw_order],
            latitude[draw_order],
            s=marker_area(magnitude[draw_order]),
            c=depth_km[draw_order],
            transform=ccrs.PlateCarree(),
            cmap="viridis",
            vmin=0,
            vmax=650,
            alpha=0.82,
            edgecolors="white",
            linewidths=0.18,
            rasterized=True,
            zorder=3,
        )
        map_ax.colorbar(
            points,
            loc="r",
            label="Hypocentral depth (km)",
            ticks=(0, 100, 300, 500, 650),
            length=0.84,
        )

        legend_magnitudes = (5, 6, 7, 8)
        legend_handles = [
            Line2D(
                [],
                [],
                linestyle="none",
                marker="o",
                markersize=float(np.sqrt(marker_area(value))),
                markerfacecolor="#4D4D4D",
                markeredgecolor="white",
                markeredgewidth=0.4,
                label=f"M{value}",
            )
            for value in legend_magnitudes
        ]
        map_ax.legend(
            handles=legend_handles,
            loc="ll",
            ncols=4,
            title="Reported magnitude",
            frame=True,
        )
        map_ax.text(
            0.985,
            0.975,
            rf"{YEAR}  |  $M\geq5$  |  $n={len(magnitude):,}$",
            transform=map_ax.transAxes,
            ha="right",
            va="top",
            color="#303030",
        )

        magnitude_positions = np.arange(4)
        magnitude_ax.bar(
            magnitude_positions,
            magnitude_counts,
            width=0.68,
            color="#D55E00",
            edgecolor="#6F2F09",
            linewidth=0.5,
        )
        magnitude_ax.format(
            xlabel="Reported magnitude class",
            ylabel="Earthquakes (log scale)",
            xlim=(-0.65, 3.65),
            ylim=(0.7, 5000),
            yscale="log",
            xticks=magnitude_positions,
            xticklabels=("5.0-5.9", "6.0-6.9", "7.0-7.9", "8.0+"),
            yticks=(1, 10, 100, 1000),
            grid=False,
            ygrid=True,
        )
        for x_value, count in zip(magnitude_positions, magnitude_counts):
            magnitude_ax.text(
                x_value,
                count * 1.22,
                f"{count:,}",
                ha="center",
                va="bottom",
                fontsize=7.2,
                color="#3A2418",
            )

        depth_positions = np.array([2, 1, 0])
        depth_midpoints = np.array([35, 185, 475])
        depth_colors = mpl.colormaps["viridis"](depth_midpoints / 650)
        depth_ax.barh(
            depth_positions,
            depth_counts,
            color=depth_colors,
            edgecolor="#454545",
            linewidth=0.5,
        )
        depth_ax.format(
            xlabel="Earthquakes",
            xlim=(0, 2250),
            ylim=(-0.65, 3.25),
            xticks=(0, 500, 1000, 1500, 2000),
            yticks=depth_positions,
            yticklabels=(
                "Shallow\n<70 km",
                "Intermediate\n70-299 km",
                "Deep\n>=300 km",
            ),
            grid=False,
            xgrid=True,
        )
        for y_value, count in zip(depth_positions, depth_counts):
            percent = 100 * count / len(depth_km)
            depth_ax.text(
                count + 35,
                y_value,
                f"{count:,}  ({percent:.1f}%)",
                ha="left",
                va="center",
                fontsize=7.2,
                color="#303030",
            )

        fig.save(OUTPUT_STEM.with_suffix(".pdf"), dpi=EXPORT_DPI)
        fig.save(OUTPUT_STEM.with_suffix(".png"), dpi=EXPORT_DPI)


if __name__ == "__main__":
    main()
