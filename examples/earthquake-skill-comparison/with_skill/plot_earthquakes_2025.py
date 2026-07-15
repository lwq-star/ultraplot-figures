"""Create a publication-ready overview of 2025 global M5+ earthquakes."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import matplotlib

matplotlib.use("Agg")

import cartopy.crs as ccrs
from matplotlib import colors as mcolors
import numpy as np
from PIL import Image
import ultraplot as uplt


# User-tunable configuration
EXAMPLE_DIR = Path(__file__).resolve().parents[1]
INPUT_GEOJSON = EXAMPLE_DIR / "data" / "usgs_earthquakes_2025_m5plus.geojson"
OUTPUT_DIR = Path(__file__).resolve().parent
OUTPUT_STEM = OUTPUT_DIR / "earthquakes_2025_m5plus"

FALLBACK_JOURNAL = "nat2"
FALLBACK_DPI = 600
FALLBACK_RC = {
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "savefig.facecolor": "white",
    "savefig.transparent": False,
}

TARGET_EVENT_TYPE = "earthquake"
DISPLAY_PROJECTION = "Robinson, central_longitude=180 degrees"
SOURCE_CRS = "GeoJSON RFC 7946 longitude/latitude (WGS 84)"
MAP_CENTRAL_LONGITUDE = 180.0
DEPTH_COLOR_MIN_KM = 0.0
DEPTH_COLOR_MAX_KM = 650.0
DEPTH_COLOR_GAMMA = 0.5
DEPTH_COLOR_TICKS_KM = [0, 10, 50, 100, 300, 600]
MAGNITUDE_SIZE_MIN_PT2 = 8.0
MAGNITUDE_SIZE_MAX_PT2 = 72.0
MAGNITUDE_LEGEND_LEVELS = np.array([5.0, 6.0, 7.0, 8.0])
MAGNITUDE_BINS = np.arange(5.0, 9.0001, 0.2)
DEPTH_BINS_KM = np.arange(0.0, 675.0, 25.0)


def _finite_numeric(value: object, field: str, feature_id: object) -> float:
    if not isinstance(value, (int, float)):
        raise ValueError(f"Feature {feature_id!r} has non-numeric {field!r}.")
    result = float(value)
    if not np.isfinite(result):
        raise ValueError(f"Feature {feature_id!r} has non-finite {field!r}.")
    return result


def load_catalog(path: Path = INPUT_GEOJSON) -> dict[str, object]:
    """Load, explicitly filter, and validate the event catalog."""
    with path.open("r", encoding="utf-8") as stream:
        document = json.load(stream)

    if document.get("type") != "FeatureCollection":
        raise ValueError("Input must be a GeoJSON FeatureCollection.")
    if document.get("crs") is not None:
        raise ValueError("Unexpected explicit GeoJSON CRS; review before plotting.")
    features = document.get("features")
    if not isinstance(features, list) or not features:
        raise ValueError("GeoJSON contains no features.")

    class_counts = Counter()
    geometry_counts = Counter()
    retained = []
    excluded_by_class = Counter()
    identifiers = []
    empty_geometries = 0

    for feature in features:
        properties = feature.get("properties") or {}
        geometry = feature.get("geometry") or {}
        event_type = properties.get("type")
        geometry_type = geometry.get("type")
        class_counts[str(event_type)] += 1
        geometry_counts[str(geometry_type)] += 1
        identifiers.append(feature.get("id"))
        if not geometry.get("coordinates"):
            empty_geometries += 1
        if event_type == TARGET_EVENT_TYPE:
            retained.append(feature)
        else:
            excluded_by_class[str(event_type)] += 1

    if geometry_counts != Counter({"Point": len(features)}):
        raise ValueError(f"Expected only Point geometry, got {dict(geometry_counts)}.")
    if empty_geometries:
        raise ValueError(f"Found {empty_geometries} empty geometries.")
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("Duplicate feature identifiers found.")
    if not retained:
        raise ValueError("No earthquake records remain after filtering.")

    longitude = []
    latitude = []
    depth_km = []
    magnitude = []
    time_utc = []
    for feature in retained:
        feature_id = feature.get("id")
        coordinates = feature["geometry"]["coordinates"]
        if len(coordinates) < 3:
            raise ValueError(f"Feature {feature_id!r} lacks coordinate depth.")
        lon = _finite_numeric(coordinates[0], "longitude", feature_id)
        lat = _finite_numeric(coordinates[1], "latitude", feature_id)
        dep = _finite_numeric(coordinates[2], "hypocentral depth", feature_id)
        mag = _finite_numeric(feature["properties"].get("mag"), "magnitude", feature_id)
        epoch_ms = _finite_numeric(feature["properties"].get("time"), "time", feature_id)
        event_time = datetime.fromtimestamp(epoch_ms / 1000.0, tz=timezone.utc)
        if not -180.0 <= lon <= 180.0:
            raise ValueError(f"Feature {feature_id!r} longitude is outside [-180, 180].")
        if not -90.0 <= lat <= 90.0:
            raise ValueError(f"Feature {feature_id!r} latitude is outside [-90, 90].")
        if dep < 0.0:
            raise ValueError(f"Feature {feature_id!r} has negative depth.")
        if mag < 5.0:
            raise ValueError(f"Feature {feature_id!r} has magnitude below 5.0.")
        if event_time.year != 2025:
            raise ValueError(f"Feature {feature_id!r} is outside calendar year 2025 UTC.")
        longitude.append(lon)
        latitude.append(lat)
        depth_km.append(dep)
        magnitude.append(mag)
        time_utc.append(event_time)

    counts = {
        "input": len(features),
        "retained": len(retained),
        "excluded": len(features) - len(retained),
        "excluded_by_class": dict(sorted(excluded_by_class.items())),
    }
    return {
        "longitude_deg": np.asarray(longitude, dtype=float),
        "latitude_deg": np.asarray(latitude, dtype=float),
        "hypocentral_depth_km": np.asarray(depth_km, dtype=float),
        "magnitude": np.asarray(magnitude, dtype=float),
        "time_utc": np.asarray(time_utc, dtype=object),
        "counts": counts,
        "class_counts": dict(sorted(class_counts.items())),
        "geometry_counts": dict(sorted(geometry_counts.items())),
        "empty_geometries": empty_geometries,
        "metadata": document.get("metadata") or {},
    }


def create_figure(data: dict[str, object]) -> tuple[object, object]:
    """Build the complete figure and return its figure and subplot container."""
    longitude = data["longitude_deg"]
    latitude = data["latitude_deg"]
    depth_km = data["hypocentral_depth_km"]
    magnitude = data["magnitude"]

    display_crs = ccrs.Robinson(central_longitude=MAP_CENTRAL_LONGITUDE)
    data_crs = ccrs.PlateCarree()
    layout = [[1, 1], [2, 3]]
    fig, axs = uplt.subplots(
        layout,
        proj={1: display_crs},
        journal=FALLBACK_JOURNAL,
        share=False,
    )
    ax_map, ax_magnitude, ax_depth = axs

    depth_norm = mcolors.PowerNorm(
        gamma=DEPTH_COLOR_GAMMA,
        vmin=DEPTH_COLOR_MIN_KM,
        vmax=DEPTH_COLOR_MAX_KM,
        clip=True,
    )
    points = ax_map.scatter(
        longitude,
        latitude,
        s=magnitude,
        smin=MAGNITUDE_SIZE_MIN_PT2,
        smax=MAGNITUDE_SIZE_MAX_PT2,
        absolute_size=False,
        c=depth_km,
        cmap="cividis",
        norm=depth_norm,
        transform=data_crs,
        edgecolors="white",
        linewidths=0.18,
        zorder=3,
    )
    ax_map.format(
        coast=True,
        lonlines=60,
        latlines=30,
        lonlabels="b",
        latlabels="l",
    )
    ax_map.colorbar(
        points,
        loc="b",
        label="Hypocentral depth (km)",
        ticks=DEPTH_COLOR_TICKS_KM,
        tickminor=False,
    )
    size_handles, size_labels = ax_map.sizelegend(
        MAGNITUDE_LEGEND_LEVELS,
        values=magnitude,
        smin=MAGNITUDE_SIZE_MIN_PT2,
        smax=MAGNITUDE_SIZE_MAX_PT2,
        add=False,
    )
    ax_map.legend(
        size_handles,
        size_labels,
        title="Magnitude",
        loc="r",
        ncols=1,
        frame=False,
        borderpad="4pt",
        handletextpad="6pt",
        labelspacing="6pt",
        columnspacing="8pt",
    )

    magnitude_counts, _ = np.histogram(magnitude, bins=MAGNITUDE_BINS)
    magnitude_centers = 0.5 * (MAGNITUDE_BINS[:-1] + MAGNITUDE_BINS[1:])
    magnitude_width = float(np.diff(MAGNITUDE_BINS)[0] * 0.9)
    ax_magnitude.bar(
        magnitude_centers,
        magnitude_counts,
        width=magnitude_width,
        absolute_width=True,
        color="#0072B2",
        edgecolor="white",
        linewidth=0.35,
    )
    ax_magnitude.format(
        xlabel="Magnitude",
        ylabel="Earthquake count (log scale)",
        xlim=(4.95, 8.85),
        xticks=[5, 6, 7, 8],
        yscale="log",
        ylim=(0.8, 1500),
    )

    depth_counts, _ = np.histogram(depth_km, bins=DEPTH_BINS_KM)
    depth_centers = 0.5 * (DEPTH_BINS_KM[:-1] + DEPTH_BINS_KM[1:])
    depth_width = float(np.diff(DEPTH_BINS_KM)[0] * 0.9)
    ax_depth.bar(
        depth_centers,
        depth_counts,
        width=depth_width,
        absolute_width=True,
        color="#D55E00",
        edgecolor="white",
        linewidth=0.35,
    )
    ax_depth.format(
        xlabel="Hypocentral depth (km)",
        ylabel="Earthquake count (log scale)",
        xlim=(0, 650),
        xticks=[0, 100, 300, 500, 650],
        yscale="log",
        ylim=(0.8, 1500),
    )
    axs.format(abc="a", abcloc="ul")
    fig.canvas.draw()

    return fig, axs


def save_publication_fallback(
    fig: matplotlib.figure.Figure,
    output_stem: Path = OUTPUT_STEM,
    *,
    dpi: int = FALLBACK_DPI,
) -> tuple[Path, Path]:
    """Save PDF plus an opaque RGB, lossless-LZW TIFF without Skill imports."""
    output_stem = Path(output_stem)
    if output_stem.suffix:
        raise ValueError("output_stem must not include a file extension")
    output_stem.parent.mkdir(parents=True, exist_ok=True)
    pdf_path = output_stem.with_suffix(".pdf")
    tiff_path = output_stem.with_suffix(".tif")

    with uplt.rc.context(FALLBACK_RC):
        fig.canvas.draw()
        fig.savefig(pdf_path, facecolor="white", transparent=False)
        with TemporaryDirectory() as tmp_dir:
            raster_path = Path(tmp_dir) / "render.png"
            fig.savefig(
                raster_path,
                dpi=dpi,
                facecolor="white",
                transparent=False,
            )
            with Image.open(raster_path) as rendered:
                rgba = rendered.convert("RGBA")
                white = Image.new("RGBA", rgba.size, "white")
                rgb = Image.alpha_composite(white, rgba).convert("RGB")
                rgb.save(
                    tiff_path,
                    format="TIFF",
                    dpi=(dpi, dpi),
                    compression="tiff_lzw",
                )
    return pdf_path, tiff_path


def summarize(data: dict[str, object], fig: object) -> dict[str, object]:
    magnitude = data["magnitude"]
    depth_km = data["hypocentral_depth_km"]
    longitude = data["longitude_deg"]
    latitude = data["latitude_deg"]
    width_mm, height_mm = fig.get_size_inches() * 25.4
    return {
        "source_crs": SOURCE_CRS,
        "display_projection": DISPLAY_PROJECTION,
        "counts": data["counts"],
        "class_counts": data["class_counts"],
        "geometry_counts": data["geometry_counts"],
        "longitude_range_deg": [float(longitude.min()), float(longitude.max())],
        "latitude_range_deg": [float(latitude.min()), float(latitude.max())],
        "magnitude_range": [float(magnitude.min()), float(magnitude.max())],
        "depth_range_km": [float(depth_km.min()), float(depth_km.max())],
        "magnitude_quantiles_0_25_50_75_100": np.quantile(
            magnitude, [0, 0.25, 0.5, 0.75, 1]
        ).tolist(),
        "depth_quantiles_km_0_25_50_75_100": np.quantile(
            depth_km, [0, 0.25, 0.5, 0.75, 1]
        ).tolist(),
        "final_size_mm": [float(width_mm), float(height_mm)],
        "tiff_dpi": FALLBACK_DPI,
        "tiff_mode": "RGB",
        "tiff_compression": "LZW",
    }


def main() -> int:
    data = load_catalog()
    with uplt.rc.context(FALLBACK_RC):
        fig, _ = create_figure(data)
        pdf_path, tiff_path = save_publication_fallback(fig)
    result = summarize(data, fig)
    result["outputs"] = {
        "python": Path(__file__).resolve().relative_to(EXAMPLE_DIR).as_posix(),
        "pdf": pdf_path.resolve().relative_to(EXAMPLE_DIR).as_posix(),
        "tiff": tiff_path.resolve().relative_to(EXAMPLE_DIR).as_posix(),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
