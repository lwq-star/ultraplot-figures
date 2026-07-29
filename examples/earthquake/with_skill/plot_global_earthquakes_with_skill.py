from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import cartopy
import cartopy.crs as ccrs
import matplotlib
from matplotlib.colors import Normalize
from matplotlib.lines import Line2D
import numpy as np
from PIL import Image
from pypdf import PdfReader
import ultraplot as uplt


OUTPUT_DIR = Path(__file__).resolve().parent
DATA_PATH = OUTPUT_DIR.parent / "data" / "usgs_earthquakes_2025_m5plus.geojson"
PDF_PATH = OUTPUT_DIR / "global_earthquakes_2025_m5plus_with_skill.pdf"
PNG_PATH = OUTPUT_DIR / "global_earthquakes_2025_m5plus_with_skill.png"
VERIFICATION_PATH = OUTPUT_DIR / "verification_with_skill.json"

EXPORT_DPI = 1000
DEPTH_MAX_KM = 650.0
MAGNITUDE_LEGEND_VALUES = (5.0, 6.0, 7.0, 8.0, 8.8)


def report_relative_path(path: Path, report_path: Path) -> str:
    return Path(os.path.relpath(path, start=report_path.parent)).as_posix()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def utc_iso(milliseconds: int) -> str:
    return datetime.fromtimestamp(milliseconds / 1000, timezone.utc).isoformat()


def marker_area(magnitude: np.ndarray | float) -> np.ndarray | float:
    """Return marker area in points squared; the legend exposes the mapping."""
    return 7.0 * np.power(2.2, np.asarray(magnitude) - 5.0)


def load_and_validate_events(path: Path) -> dict[str, object]:
    with path.open("r", encoding="utf-8") as stream:
        collection = json.load(stream)

    if collection.get("type") != "FeatureCollection":
        raise ValueError("Expected a GeoJSON FeatureCollection.")
    if collection.get("crs") is not None:
        raise ValueError("Unexpected legacy GeoJSON CRS member; inspect before plotting.")

    features = collection.get("features", [])
    if not features:
        raise ValueError("The GeoJSON contains no earthquake features.")
    if any(feature.get("geometry", {}).get("type") != "Point" for feature in features):
        raise ValueError("Every earthquake feature must have Point geometry.")

    coordinates = np.asarray(
        [feature["geometry"]["coordinates"] for feature in features], dtype=float
    )
    magnitudes = np.asarray(
        [feature["properties"]["mag"] for feature in features], dtype=float
    )
    times = np.asarray(
        [feature["properties"]["time"] for feature in features], dtype=np.int64
    )

    if coordinates.shape != (len(features), 3):
        raise ValueError("Expected longitude, latitude, and depth for every event.")
    if not np.isfinite(coordinates).all() or not np.isfinite(magnitudes).all():
        raise ValueError("Coordinates, depths, and magnitudes must all be finite.")

    longitudes = coordinates[:, 0]
    latitudes = coordinates[:, 1]
    depths_km = coordinates[:, 2]
    if np.any((longitudes < -180) | (longitudes > 180)):
        raise ValueError("Longitude lies outside the WGS84 domain.")
    if np.any((latitudes < -90) | (latitudes > 90)):
        raise ValueError("Latitude lies outside the WGS84 domain.")
    if np.any(depths_km < 0):
        raise ValueError("Negative hypocentral depth found.")
    if np.any(magnitudes < 5):
        raise ValueError("The input is not consistently M5+.")

    years = np.asarray(
        [datetime.fromtimestamp(value / 1000, timezone.utc).year for value in times]
    )
    if not np.all(years == 2025):
        raise ValueError("The input is not consistently restricted to 2025 UTC.")

    expected_bbox = np.asarray(collection.get("bbox"), dtype=float)
    observed_bbox = np.asarray(
        [
            longitudes.min(),
            latitudes.min(),
            depths_km.min(),
            longitudes.max(),
            latitudes.max(),
            depths_km.max(),
        ]
    )
    if expected_bbox.shape != (6,) or not np.allclose(expected_bbox, observed_bbox):
        raise ValueError("GeoJSON bbox does not match the event coordinates.")

    metadata = collection.get("metadata", {})
    query_url = str(metadata.get("url", ""))
    required_query_terms = (
        "format=geojson",
        "starttime=2025-01-01",
        "endtime=2026-01-01",
        "minmagnitude=5",
    )
    if not all(term in query_url for term in required_query_terms):
        raise ValueError("USGS query metadata does not match the intended population.")

    return {
        "longitudes": longitudes,
        "latitudes": latitudes,
        "depths_km": depths_km,
        "magnitudes": magnitudes,
        "times": times,
        "metadata": metadata,
    }


def build_figure(events: dict[str, object]):
    longitudes = np.asarray(events["longitudes"])
    latitudes = np.asarray(events["latitudes"])
    depths_km = np.asarray(events["depths_km"])
    magnitudes = np.asarray(events["magnitudes"])

    # Small events are drawn first so rare large events remain legible.
    order = np.argsort(magnitudes, kind="stable")
    source_crs = ccrs.PlateCarree()
    depth_norm = Normalize(vmin=0.0, vmax=DEPTH_MAX_KM)

    fig, ax = uplt.subplots(proj="pcarree", journal="nat2")
    ax.set_global()
    points = ax.scatter(
        longitudes[order],
        latitudes[order],
        s=marker_area(magnitudes[order]),
        c=depths_km[order],
        cmap="batlow",
        norm=depth_norm,
        transform=source_crs,
        alpha=0.84,
        edgecolors="black",
        linewidths=0.16,
        rasterized=True,
        zorder=3,
    )

    ax.format(
        coast=True,
        land=True,
        landcolor="0.93",
        ocean=True,
        oceancolor="white",
        grid=True,
        lonlabels="b",
        latlabels="l",
        lonlocator=60,
        latlocator=30,
    )
    fig.colorbar(
        points,
        loc="r",
        label="Hypocentral depth (km)",
        ticks=np.arange(0, 601, 100),
    )

    legend_handles = [
        Line2D(
            [0],
            [0],
            marker="o",
            linestyle="none",
            markersize=float(np.sqrt(marker_area(value))),
            markerfacecolor="0.5",
            markeredgecolor="black",
            markeredgewidth=0.4,
        )
        for value in MAGNITUDE_LEGEND_VALUES
    ]
    legend_labels = [f"{value:g}" for value in MAGNITUDE_LEGEND_VALUES]
    ax.legend(
        handles=legend_handles,
        labels=legend_labels,
        loc="b",
        ncols=len(legend_handles),
        title="Magnitude",
    )

    return fig, ax


def verify_and_record(
    fig,
    ax,
    events: dict[str, object],
    source_hash_before: str,
    rc_before: dict[str, object],
) -> None:
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    figure_width_in, figure_height_in = fig.get_size_inches()
    frame = ax.get_position()
    tight = ax.get_tightbbox(renderer)
    canvas_width_px, canvas_height_px = fig.canvas.get_width_height()

    title_texts = (
        ax.get_title(loc="left"),
        ax.get_title(loc="center"),
        ax.get_title(loc="right"),
    )
    suptitle_text = fig._suptitle.get_text() if fig._suptitle is not None else ""
    if any(title_texts) or suptitle_text:
        raise RuntimeError("Unrequested figure or subplot title is present.")

    fig.save(PDF_PATH, dpi=EXPORT_DPI)
    fig.save(PNG_PATH, dpi=EXPORT_DPI)

    with Image.open(PNG_PATH) as png:
        png_size = list(png.size)
        png_mode = png.mode
        png_dpi = [float(value) for value in png.info.get("dpi", (0.0, 0.0))]
        extrema = png.convert("RGB").getextrema()
        nonblank = any(high > low for low, high in extrema)

    reader = PdfReader(str(PDF_PATH))
    page = reader.pages[0]
    pdf_width_pt = float(page.mediabox.width)
    pdf_height_pt = float(page.mediabox.height)
    pdf_width_mm = pdf_width_pt / 72 * 25.4
    pdf_height_mm = pdf_height_pt / 72 * 25.4

    expected_png_width = round(figure_width_in * EXPORT_DPI)
    if abs(pdf_width_mm - 183.0) > 0.2:
        raise RuntimeError(f"PDF width is {pdf_width_mm:.4f} mm, not 183 mm.")
    if abs(png_size[0] - expected_png_width) > 1:
        raise RuntimeError("PNG width does not match figure width at 1000 dpi.")
    if min(png_dpi) < 999.0:
        raise RuntimeError("PNG metadata does not record the requested 1000 dpi.")
    if not nonblank:
        raise RuntimeError("PNG appears blank.")
    if len(reader.pages) != 1:
        raise RuntimeError("PDF must contain exactly one page.")
    if source_hash_before != sha256(DATA_PATH):
        raise RuntimeError("The source GeoJSON changed during plotting.")

    longitudes = np.asarray(events["longitudes"])
    latitudes = np.asarray(events["latitudes"])
    depths_km = np.asarray(events["depths_km"])
    magnitudes = np.asarray(events["magnitudes"])
    times = np.asarray(events["times"])

    report = {
        "path_base": "directory_containing_this_json",
        "scientific_question": (
            "Where did global M5+ earthquakes occur in 2025, and how did "
            "their magnitude and hypocentral depth vary spatially?"
        ),
        "intended_message": (
            "Readers can compare global clustering while reading magnitude "
            "from marker area and depth from a perceptually uniform color scale."
        ),
        "environment": {
            "ultraplot": uplt.__version__,
            "matplotlib": matplotlib.__version__,
            "cartopy": cartopy.__version__,
        },
        "source": {
            "path": report_relative_path(DATA_PATH, VERIFICATION_PATH),
            "sha256": source_hash_before,
            "feature_count": int(longitudes.size),
            "geometry": "3D Point",
            "horizontal_crs": (
                "WGS84 longitude/latitude from USGS RFC 7946 GeoJSON; "
                "displayed directly as EPSG:4326"
            ),
            "vertical_coordinate": (
                "Source third ordinate retained as hypocentral depth in km; "
                "it is not treated as ellipsoidal height"
            ),
            "bounds": {
                "longitude": [float(longitudes.min()), float(longitudes.max())],
                "latitude": [float(latitudes.min()), float(latitudes.max())],
                "depth_km": [float(depths_km.min()), float(depths_km.max())],
            },
            "magnitude_range": [float(magnitudes.min()), float(magnitudes.max())],
            "time_range_utc": [utc_iso(int(times.min())), utc_iso(int(times.max()))],
            "missing_coordinate_or_magnitude_values": 0,
            "processing": (
                "None. All raw events are plotted; stable magnitude sorting "
                "changes draw order only."
            ),
        },
        "encodings": {
            "position": "WGS84 longitude and latitude",
            "marker_area": "Magnitude; exact reference values shown in legend",
            "marker_color": "Hypocentral depth (km), batlow sequential colormap",
            "depth_normalization_km": [0.0, DEPTH_MAX_KM],
        },
        "layout": {
            "topology": "One fixed-aspect global GeoAxes",
            "width_authority": 'journal="nat2" (183 mm)',
            "manual_spacing_overrides": [],
            "figure_inches": [float(figure_width_in), float(figure_height_in)],
            "canvas_pixels_before_export": [canvas_width_px, canvas_height_px],
            "visible_frame_inches": [
                float(frame.width * figure_width_in),
                float(frame.height * figure_height_in),
            ],
            "axes_tight_bbox_inches": [
                float(tight.width / fig.dpi),
                float(tight.height / fig.dpi),
            ],
        },
        "style_audit": {
            "rc_changed_before": {key: repr(value) for key, value in rc_before.items()},
            "rc_changed_after": {
                key: repr(value) for key, value in uplt.rc.changed.items()
            },
            "figure_local_overrides": [
                (
                    "Light-gray land and white ocean preserve contrast for the "
                    "dark shallow-depth end of the batlow data colormap."
                )
            ],
            "figure_or_subplot_titles": [],
        },
        "outputs": {
            "export_dpi": EXPORT_DPI,
            "png": {
                "path": report_relative_path(PNG_PATH, VERIFICATION_PATH),
                "pixels": png_size,
                "mode": png_mode,
                "dpi_metadata": png_dpi,
                "nonblank": nonblank,
                "sha256": sha256(PNG_PATH),
            },
            "pdf": {
                "path": report_relative_path(PDF_PATH, VERIFICATION_PATH),
                "pages": len(reader.pages),
                "media_box_points": [pdf_width_pt, pdf_height_pt],
                "physical_size_mm": [pdf_width_mm, pdf_height_mm],
                "sha256": sha256(PDF_PATH),
            },
        },
    }
    VERIFICATION_PATH.write_text(
        json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8"
    )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    source_hash_before = sha256(DATA_PATH)
    rc_before = dict(uplt.rc.changed)
    events = load_and_validate_events(DATA_PATH)
    fig, ax = build_figure(events)
    verify_and_record(fig, ax, events, source_hash_before, rc_before)
    uplt.close(fig)
    print(f"Saved: {PDF_PATH}")
    print(f"Saved: {PNG_PATH}")
    print(f"Saved: {VERIFICATION_PATH}")


if __name__ == "__main__":
    main()
