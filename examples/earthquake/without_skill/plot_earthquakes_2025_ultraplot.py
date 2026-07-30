# -*- coding: utf-8 -*-
"""Plot the global distribution of 2025 M5+ earthquakes with UltraPlot.

The script reads a USGS GeoJSON FeatureCollection, keeps Point features whose
USGS ``type`` is ``earthquake``, validates their core fields, and exports a
publication-size PNG and vector PDF.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Use a bundled GDAL data directory when the active environment provides one.
_gdal_data = Path(sys.prefix) / "Library" / "share" / "gdal"
if _gdal_data.is_dir():
    os.environ.setdefault("GDAL_DATA", str(_gdal_data))

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib as mpl
import numpy as np
import ultraplot as uplt
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.patches import Patch


DEFAULT_INPUT = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "usgs_earthquakes_2025_m5plus.geojson"
)
OUTPUT_STEM = "earthquakes_2025_m5plus_global"
PDF_METADATA = {
    "Creator": "UltraPlot",
    "Producer": "UltraPlot",
    "CreationDate": None,
}
PNG_METADATA = {"Software": "UltraPlot"}
DEPTH_EDGES = np.array([0.0, 35.0, 70.0, 150.0, 300.0, 650.0])
DEPTH_LABELS = ["0-34", "35-69", "70-149", "150-299", "300-650"]
DEPTH_COLORS = ["#F5CF55", "#F0954A", "#DF5A4F", "#9A4D79", "#355F8A"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="USGS GeoJSON input (default: supplied 2025 M5+ file)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="Directory for PNG and PDF outputs (default: script directory)",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=300,
        help="PNG resolution in dots per inch (default: 300)",
    )
    return parser.parse_args()


def load_earthquakes(path: Path) -> dict[str, np.ndarray | list[str] | int]:
    with path.open("r", encoding="utf-8") as stream:
        collection = json.load(stream)

    if collection.get("type") != "FeatureCollection":
        raise ValueError("Input is not a GeoJSON FeatureCollection.")

    rows: list[tuple[float, float, float, float, int, str]] = []
    excluded_non_earthquakes = 0
    for index, feature in enumerate(collection.get("features", [])):
        props = feature.get("properties") or {}
        if props.get("type") != "earthquake":
            excluded_non_earthquakes += 1
            continue
        geometry = feature.get("geometry") or {}
        coordinates = geometry.get("coordinates") or []
        if geometry.get("type") != "Point" or len(coordinates) < 3:
            raise ValueError(f"Feature {index} lacks a 3D Point geometry.")
        if props.get("mag") is None or props.get("time") is None:
            raise ValueError(f"Feature {index} lacks magnitude or origin time.")

        lon, lat, depth = map(float, coordinates[:3])
        mag = float(props["mag"])
        origin_ms = int(props["time"])
        place = str(props.get("place") or "Unknown location")
        if not (-180.0 <= lon <= 180.0 and -90.0 <= lat <= 90.0):
            raise ValueError(f"Feature {index} has invalid longitude/latitude.")
        if depth < 0.0 or mag < 5.0:
            raise ValueError(f"Feature {index} violates the expected M5+ data range.")
        year = datetime.fromtimestamp(origin_ms / 1000, tz=timezone.utc).year
        if year != 2025:
            raise ValueError(f"Feature {index} has a non-2025 UTC origin time.")
        rows.append((lon, lat, depth, mag, origin_ms, place))

    if not rows:
        raise ValueError("No valid earthquake Point features were found.")

    return {
        "longitude": np.array([row[0] for row in rows]),
        "latitude": np.array([row[1] for row in rows]),
        "depth": np.array([row[2] for row in rows]),
        "magnitude": np.array([row[3] for row in rows]),
        "origin_ms": np.array([row[4] for row in rows], dtype=np.int64),
        "place": [row[5] for row in rows],
        "excluded_non_earthquakes": excluded_non_earthquakes,
    }


def marker_area(magnitude: np.ndarray | float) -> np.ndarray:
    values = np.asarray(magnitude, dtype=float)
    return 11.0 + 11.5 * np.square(np.maximum(values - 4.8, 0.0))


def configure_style() -> None:
    font_fallbacks = [
        "Noto Sans SC",
        "Microsoft YaHei",
        "SimHei",
        "DejaVu Sans",
    ]
    settings = {
            "font.name": "Noto Sans SC",
            "font.family": ["Noto Sans SC"],
            "font.sans-serif": font_fallbacks,
            "axes.unicode_minus": False,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "figure.facecolor": "#FAFAF7",
            "savefig.facecolor": "#FAFAF7",
            "axes.titleweight": "semibold",
            "axes.labelcolor": "#263238",
            "text.color": "#1F2A30",
            "xtick.color": "#526168",
            "ytick.color": "#526168",
    }
    uplt.rc.update(settings)
    mpl.rcParams.update({key: value for key, value in settings.items() if key != "font.name"})


def add_log_count_bars(
    ax,
    labels: list[str],
    counts: np.ndarray,
    colors: list[str],
    total: int,
    title: str,
    note: str,
) -> None:
    y = np.arange(len(labels))
    ax.barh(
        np.maximum(counts - 1, 0),
        left=1,
        width=0.66,
        absolute_width=True,
        color=colors,
        edgecolor="white",
        linewidth=0.8,
        zorder=3,
    )
    ax.set_xscale("log")
    ax.set_xlim(1, 3000)
    ax.set_xticks([1, 10, 100, 1000])
    ax.get_xaxis().set_major_formatter(mpl.ticker.StrMethodFormatter("{x:,.0f}"))
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_xlabel("事件数（对数尺度）", fontsize=9)
    ax.set_title(title, loc="left", fontsize=13, pad=11)
    ax.text(
        1.0,
        1.035,
        note,
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=9,
        color="#5B676D",
    )
    for yi, count in zip(y, counts, strict=True):
        pct = 100.0 * count / total
        is_large = count >= 800
        ax.text(
            float(count) / 1.08 if is_large else min(float(count) * 1.12, 2350),
            yi,
            f"{count:,}  {pct:.1f}%",
            va="center",
            ha="right" if is_large else "left",
            fontsize=8.5,
            color="#28363C",
        )
    ax.grid(axis="x", which="major", color="#D6DDDF", linewidth=0.65, zorder=0)
    ax.grid(axis="x", which="minor", visible=False)
    ax.tick_params(axis="both", labelsize=9, length=0)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color("#B8C2C5")
    ax.set_facecolor("#FAFAF7")


def make_figure(data: dict[str, np.ndarray | list[str] | int]):
    lon = np.asarray(data["longitude"])
    lat = np.asarray(data["latitude"])
    depth = np.asarray(data["depth"])
    mag = np.asarray(data["magnitude"])
    origin_ms = np.asarray(data["origin_ms"])
    places = list(data["place"])
    count = len(mag)

    configure_style()
    projection = ccrs.Robinson(central_longitude=150)
    fig, axs = uplt.subplots(
        [[1, 1], [2, 3]],
        proj={1: projection},
        figsize=(16, 10),
        hratios=(2.15, 1.0),
        left="0.65in",
        right="0.30in",
        top="1.15in",
        bottom="0.62in",
        wspace="0.52in",
        hspace="0.48in",
        share=False,
        tight=False,
    )
    ax_map, ax_mag, ax_depth = axs

    fig.text(
        0.052,
        0.958,
        "2025年全球 M5.0+ 地震",
        ha="left",
        va="top",
        fontsize=25,
        fontweight="bold",
        color="#17262D",
    )
    shallow_pct = 100.0 * np.mean(depth < 70.0)
    subtitle = (
        f"{count:,} 次地震  |  最大 M{mag.max():.1f}  |  "
        f"{shallow_pct:.1f}% 深度小于 70 km  |  "
        "点大小表示震级，颜色表示震源深度"
    )
    fig.text(0.052, 0.906, subtitle, ha="left", va="center", fontsize=11.5, color="#526168")

    ax_map.set_global()
    ax_map.set_facecolor("#DDECF1")
    ax_map.add_feature(
        cfeature.LAND.with_scale("110m"),
        facecolor="#F1F0E9",
        edgecolor="none",
        zorder=0,
    )
    ax_map.coastlines(resolution="110m", color="#68767A", linewidth=0.52, zorder=2)
    gridliner = ax_map.gridlines(
        crs=ccrs.PlateCarree(),
        xlocs=np.arange(-180, 181, 30),
        ylocs=np.arange(-60, 61, 30),
        linewidth=0.42,
        color="#8EA3AA",
        alpha=0.55,
        linestyle=(0, (2, 3)),
        zorder=1,
    )
    gridliner.xlines = True
    gridliner.ylines = True

    cmap = ListedColormap(DEPTH_COLORS, name="earthquake_depth")
    norm = BoundaryNorm(DEPTH_EDGES, cmap.N, clip=True)
    draw_order = np.argsort(mag)
    points = ax_map.scatter(
        lon[draw_order],
        lat[draw_order],
        s=marker_area(mag[draw_order]),
        c=depth[draw_order],
        cmap=cmap,
        norm=norm,
        transform=ccrs.PlateCarree(),
        alpha=0.80,
        edgecolors="#FFFDF8",
        linewidths=0.28,
        zorder=4,
    )

    max_index = int(np.argmax(mag))
    max_date = datetime.fromtimestamp(
        int(origin_ms[max_index]) / 1000, tz=timezone.utc
    ).strftime("%Y-%m-%d")
    ax_map.scatter(
        [lon[max_index]],
        [lat[max_index]],
        s=marker_area(mag[max_index]) * 1.34,
        facecolors="none",
        edgecolors="#521E18",
        linewidths=1.4,
        transform=ccrs.PlateCarree(),
        zorder=6,
    )
    annotation_transform = ccrs.PlateCarree()._as_mpl_transform(ax_map)
    max_place = places[max_index].replace("2025 ", "").replace(" Earthquake", "")
    ax_map.annotate(
        f"年度最大：M{mag[max_index]:.1f}\n{max_place} · {max_date}",
        xy=(lon[max_index], lat[max_index]),
        xycoords=annotation_transform,
        xytext=(34, 25),
        textcoords="offset points",
        ha="left",
        va="bottom",
        fontsize=9,
        fontweight="semibold",
        color="#3D2925",
        arrowprops={
            "arrowstyle": "-",
            "color": "#6C4B43",
            "linewidth": 0.8,
            "shrinkA": 3,
            "shrinkB": 5,
        },
        bbox={
            "boxstyle": "round,pad=0.35,rounding_size=0.12",
            "facecolor": "#FFFEFA",
            "edgecolor": "#C9B8B0",
            "linewidth": 0.7,
            "alpha": 0.94,
        },
        zorder=7,
    )

    depth_handles = [
        Patch(facecolor=color, edgecolor="#FFFDF8", linewidth=0.6)
        for color in DEPTH_COLORS
    ]
    depth_legend = ax_map.legend(
        depth_handles,
        DEPTH_LABELS,
        title="震源深度（km）",
        loc="lower left",
        bbox_to_anchor=(0.055, 0.030),
        ncols=5,
        frameon=False,
        fontsize=7.8,
        title_fontsize=8.5,
        handlelength=1.15,
        handleheight=0.9,
        handletextpad=0.3,
        columnspacing=0.65,
        borderaxespad=0,
    )
    depth_legend._legend_box.align = "left"
    ax_map.add_artist(depth_legend)

    legend_values = [5.0, 6.0, 7.0, 8.0]
    legend_handles = [
        ax_map.scatter(
            [],
            [],
            s=marker_area(value),
            facecolor="#617D89",
            edgecolor="#FFFDF8",
            linewidth=0.45,
            alpha=0.88,
        )
        for value in legend_values
    ]
    magnitude_legend = ax_map.legend(
        legend_handles,
        [f"M{value:.0f}" for value in legend_values],
        title="震级",
        loc="lower right",
        bbox_to_anchor=(0.97, 0.035),
        ncols=4,
        frameon=False,
        fontsize=8,
        title_fontsize=8.5,
        handletextpad=0.25,
        columnspacing=0.75,
        borderaxespad=0,
    )
    magnitude_legend._legend_box.align = "left"

    magnitude_edges = np.array([5.0, 5.5, 6.0, 6.5, 7.0, 9.0])
    magnitude_labels = ["5.0-5.4", "5.5-5.9", "6.0-6.4", "6.5-6.9", "M7.0+"]
    magnitude_counts = np.histogram(mag, bins=magnitude_edges)[0]
    magnitude_colors = ["#C9DCE2", "#9FC4CF", "#70A8B7", "#467E91", "#C84B42"]
    add_log_count_bars(
        ax_mag,
        magnitude_labels,
        magnitude_counts,
        magnitude_colors,
        count,
        "震级构成",
        f"M6.0+：{np.sum(mag >= 6.0):,} 次  |  M7.0+：{np.sum(mag >= 7.0):,} 次",
    )

    depth_counts = np.histogram(depth, bins=DEPTH_EDGES)[0]
    add_log_count_bars(
        ax_depth,
        ["0-34 浅源", "35-69", "70-149", "150-299", "300-650 深源"],
        depth_counts,
        DEPTH_COLORS,
        count,
        "震源深度构成",
        f"中位深度：{np.median(depth):.0f} km  |  最深：{depth.max():.0f} km",
    )

    first_date = datetime.fromtimestamp(origin_ms.min() / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    last_date = datetime.fromtimestamp(origin_ms.max() / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    fig.text(
        0.052,
        0.025,
        f"数据：USGS GeoJSON  |  UTC {first_date} 至 {last_date}  |  "
        f"仅保留 type=earthquake（排除 {data['excluded_non_earthquakes']} 条非地震记录）",
        ha="left",
        va="center",
        fontsize=8,
        color="#657279",
    )
    fig.text(
        0.981,
        0.025,
        "太平洋居中 Robinson 投影  |  UltraPlot",
        ha="right",
        va="center",
        fontsize=8,
        color="#657279",
    )
    return fig


def main() -> None:
    args = parse_args()
    if args.dpi <= 0:
        raise ValueError("--dpi must be a positive integer.")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    data = load_earthquakes(args.input)
    figure = make_figure(data)

    png_path = args.output_dir / f"{OUTPUT_STEM}.png"
    pdf_path = args.output_dir / f"{OUTPUT_STEM}.pdf"
    figure.savefig(
        png_path,
        dpi=args.dpi,
        facecolor=figure.get_facecolor(),
        metadata=PNG_METADATA,
    )
    figure.savefig(
        pdf_path,
        facecolor=figure.get_facecolor(),
        metadata=PDF_METADATA,
    )
    mpl.pyplot.close(figure)

    magnitude = np.asarray(data["magnitude"])
    depth = np.asarray(data["depth"])
    print(f"Earthquakes plotted: {len(magnitude):,}")
    print(f"Magnitude range: {magnitude.min():.1f}-{magnitude.max():.1f}")
    print(f"Depth range: {depth.min():.1f}-{depth.max():.1f} km")
    print(f"PNG: {png_path.name}")
    print(f"PDF: {pdf_path.name}")


if __name__ == "__main__":
    main()
