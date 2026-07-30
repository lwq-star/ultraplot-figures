"""Render the 2025 global M >= 5 earthquake distribution with UltraPlot."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import cartopy.crs as ccrs
from matplotlib.colors import Normalize
from matplotlib.lines import Line2D
from matplotlib.text import Text
from matplotlib.transforms import Bbox
import numpy as np
import ultraplot as uplt


EXPORT_DPI = 1000
JOURNAL_PRESET = "nat2"
EXPECTED_WIDTH_MM = 183.0
DEPTH_CMAP = "batlow"
MAP_LATITUDE_LIMITS = (-70.0, 90.0)
MARKER_AREA_BASE = 11.0
MARKER_AREA_PER_MAGNITUDE = 30.0
PDF_METADATA = {
    "Creator": "UltraPlot",
    "Producer": "UltraPlot",
    "CreationDate": None,
}
PNG_METADATA = {"Software": "UltraPlot"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def marker_area(magnitude: np.ndarray | float) -> np.ndarray | float:
    return MARKER_AREA_BASE + MARKER_AREA_PER_MAGNITUDE * (
        np.asarray(magnitude) - 5.0
    )


def validate_processed_data(
    events: list[dict[str, str]],
    excluded: list[dict[str, str]],
    longitude: np.ndarray,
    latitude: np.ndarray,
    depth: np.ndarray,
    magnitude: np.ndarray,
    thresholds: np.ndarray,
    exceedance_counts: np.ndarray,
    depth_classes: list[dict[str, str]],
) -> None:
    if not events:
        raise ValueError("The processed event table is empty.")
    if len({row["event_id"] for row in events}) != len(events):
        raise ValueError("The processed event table contains duplicate event ids.")
    if any(row["event_type"] != "earthquake" for row in events):
        raise ValueError("The processed event table contains a non-earthquake event.")
    if any(not row["time_utc"].startswith("2025-") for row in events):
        raise ValueError("The processed event table contains an event outside UTC 2025.")

    numeric_arrays = [longitude, latitude, depth, magnitude, thresholds]
    if any(not np.all(np.isfinite(values)) for values in numeric_arrays):
        raise ValueError("A processed numeric column contains a non-finite value.")
    if np.any((longitude < -180.0) | (longitude > 180.0)):
        raise ValueError("Processed longitudes fall outside [-180, 180].")
    if np.any((latitude < -90.0) | (latitude > 90.0)):
        raise ValueError("Processed latitudes fall outside [-90, 90].")
    if np.any(depth < 0.0) or np.any(magnitude < 5.0):
        raise ValueError("Processed events violate the nonnegative-depth or M >= 5 filter.")

    expected_thresholds = np.arange(
        50, int(np.ceil(float(magnitude.max()) * 10.0)) + 1, dtype=float
    ) / 10.0
    if thresholds.shape != expected_thresholds.shape or not np.allclose(
        thresholds, expected_thresholds, atol=1e-12, rtol=0.0
    ):
        raise ValueError("Magnitude thresholds are not the expected 0.1-unit sequence.")
    expected_exceedance = np.asarray(
        [np.count_nonzero(magnitude >= value) for value in thresholds], dtype=int
    )
    if not np.array_equal(exceedance_counts, expected_exceedance):
        raise ValueError("Magnitude exceedance counts do not match the event table.")

    class_specs = [
        ("Shallow", 0.0, 70.0),
        ("Intermediate", 70.0, 300.0),
        ("Deep", 300.0, None),
    ]
    if [row["class_name"] for row in depth_classes] != [
        spec[0] for spec in class_specs
    ]:
        raise ValueError("Depth classes are missing or out of order.")
    for row, (_, lower, upper) in zip(depth_classes, class_specs, strict=True):
        mask = depth >= lower
        if upper is not None:
            mask &= depth < upper
        class_depth = depth[mask]
        expected_count = int(mask.sum())
        expected_percent = float(100.0 * mask.mean())
        expected_median = float(np.median(class_depth))
        if int(row["event_count"]) != expected_count:
            raise ValueError(f"Depth-class count mismatch for {row['class_name']}.")
        if not math.isclose(
            float(row["event_percent"]), expected_percent, abs_tol=1e-10
        ):
            raise ValueError(f"Depth-class percentage mismatch for {row['class_name']}.")
        if not math.isclose(
            float(row["median_depth_km"]), expected_median, abs_tol=1e-10
        ):
            raise ValueError(f"Depth-class median mismatch for {row['class_name']}.")

    retained_ids = {row["event_id"] for row in events}
    if any(not row.get("reason") for row in excluded):
        raise ValueError("An excluded feature lacks an exclusion reason.")
    if any(row["event_id"] in retained_ids for row in excluded):
        raise ValueError("An event id appears in both retained and excluded tables.")


def visible_text_bbox(text: Text, renderer) -> Bbox:
    parts = [text.get_window_extent(renderer)]
    patch = text.get_bbox_patch()
    if patch is not None and patch.get_visible():
        parts.append(patch.get_window_extent(renderer))
    return Bbox.union(parts)


def bbox_dict(bbox: Bbox, dpi: float) -> dict[str, float]:
    return {
        "x0_px": float(bbox.x0),
        "y0_px": float(bbox.y0),
        "x1_px": float(bbox.x1),
        "y1_px": float(bbox.y1),
        "width_in": float(bbox.width / dpi),
        "height_in": float(bbox.height / dpi),
    }


def overlap_area(first: Bbox, second: Bbox) -> float:
    width = max(0.0, min(first.x1, second.x1) - max(first.x0, second.x0))
    height = max(0.0, min(first.y1, second.y1) - max(first.y0, second.y0))
    return float(width * height)


def validate_layout(
    fig,
    main_axes: list,
    annotations: dict[str, list],
    legend,
) -> dict:
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    dpi = float(fig.dpi)
    fig_width_in, fig_height_in = map(float, fig.get_size_inches())
    canvas = Bbox.from_bounds(0.0, 0.0, float(fig.bbox.width), float(fig.bbox.height))
    expected_labels = ["a.", "b.", "c."]
    failures: list[str] = []

    numbers = [int(ax.number) for ax in main_axes]
    if numbers != [1, 2, 3]:
        failures.append(f"Main Axes numbers are {numbers}, expected [1, 2, 3].")

    axes_checks = []
    tight_boxes: list[Bbox] = []
    frame_boxes: list[Bbox] = []
    for ax, expected_label in zip(main_axes, expected_labels):
        slot_fraction = ax.get_subplotspec().get_position(fig)
        frame_fraction = ax.get_position()
        slot = Bbox.from_extents(
            slot_fraction.x0 * fig.bbox.width,
            slot_fraction.y0 * fig.bbox.height,
            slot_fraction.x1 * fig.bbox.width,
            slot_fraction.y1 * fig.bbox.height,
        )
        frame = ax.get_window_extent(renderer)
        tight = ax.get_tightbbox(renderer)
        tight_boxes.append(tight)
        frame_boxes.append(frame)

        slot_width_in = float(slot_fraction.width * fig_width_in)
        slot_height_in = float(slot_fraction.height * fig_height_in)
        frame_width_in = float(frame_fraction.width * fig_width_in)
        frame_height_in = float(frame_fraction.height * fig_height_in)
        width_utilization = frame_width_in / slot_width_in
        height_utilization = frame_height_in / slot_height_in

        matches = [
            text
            for text in ax.findobj(match=Text)
            if text.get_visible() and text.get_text() == expected_label
        ]
        if len(matches) != 1:
            failures.append(
                f"Axes {ax.number} has {len(matches)} {expected_label!r} identifiers; expected 1."
            )
            identifier_record = {
                "expected": expected_label,
                "detected_count": len(matches),
            }
        else:
            abc_bbox = visible_text_bbox(matches[0], renderer)
            clearance_px = 2.0 * dpi / 72.0
            reserved = Bbox.from_extents(
                abc_bbox.x0 - clearance_px,
                abc_bbox.y0 - clearance_px,
                abc_bbox.x1 + clearance_px,
                abc_bbox.y1 + clearance_px,
            )
            inside_frame = bool(
                abc_bbox.x0 >= frame.x0 - 1.0
                and abc_bbox.x1 <= frame.x1 + 1.0
                and abc_bbox.y0 >= frame.y0 - 1.0
                and abc_bbox.y1 <= frame.y1 + 1.0
            )
            upper_left = bool(
                abc_bbox.x0 < frame.x0 + 0.25 * frame.width
                and abc_bbox.y1 > frame.y0 + 0.75 * frame.height
            )
            if not inside_frame:
                failures.append(f"Identifier {expected_label} is outside its visible axes frame.")
            if not upper_left:
                failures.append(f"Identifier {expected_label} is not in the upper-left region.")

            collision_records = []
            for artist in annotations.get(expected_label, []):
                artist_bbox = (
                    visible_text_bbox(artist, renderer)
                    if isinstance(artist, Text)
                    else artist.get_window_extent(renderer)
                )
                collision = reserved.overlaps(artist_bbox)
                collision_records.append(
                    {
                        "artist_type": type(artist).__name__,
                        "overlaps_reserved_identifier_region": bool(collision),
                        "bbox": bbox_dict(artist_bbox, dpi),
                    }
                )
                if collision:
                    failures.append(
                        f"A lower-priority {type(artist).__name__} overlaps {expected_label}."
                    )
            identifier_record = {
                "expected": expected_label,
                "detected_count": 1,
                "bbox": bbox_dict(abc_bbox, dpi),
                "inside_visible_frame": inside_frame,
                "in_upper_left_region": upper_left,
                "clearance_points": 2.0,
                "lower_priority_collisions": collision_records,
            }

        titles = {
            location: ax.get_title(loc=location)
            for location in ("left", "center", "right")
        }
        if any(titles.values()):
            failures.append(f"Axes {ax.number} contains an unauthorized title: {titles}.")

        contained = bool(
            tight.x0 >= canvas.x0 - 1.0
            and tight.y0 >= canvas.y0 - 1.0
            and tight.x1 <= canvas.x1 + 1.0
            and tight.y1 <= canvas.y1 + 1.0
        )
        if not contained:
            failures.append(f"Axes {ax.number} tight bbox is outside the canvas.")
        if frame_width_in < (5.0 if ax.number == 1 else 2.0):
            failures.append(f"Axes {ax.number} visible frame is too narrow for the design.")
        if frame_height_in < (2.3 if ax.number == 1 else 1.25):
            failures.append(f"Axes {ax.number} visible frame is too short for the design.")

        axes_checks.append(
            {
                "number": int(ax.number),
                "classification": "independent main Axes",
                "slot": bbox_dict(slot, dpi),
                "visible_frame": bbox_dict(frame, dpi),
                "decorated_tight_bbox": bbox_dict(tight, dpi),
                "slot_width_in": slot_width_in,
                "slot_height_in": slot_height_in,
                "frame_width_in": frame_width_in,
                "frame_height_in": frame_height_in,
                "width_utilization": float(width_utilization),
                "height_utilization": float(height_utilization),
                "canvas_contained": contained,
                "titles": titles,
                "identifier": identifier_record,
            }
        )

    decorated_overlaps = []
    for first_index in range(len(main_axes)):
        for second_index in range(first_index + 1, len(main_axes)):
            area_px2 = overlap_area(tight_boxes[first_index], tight_boxes[second_index])
            overlap = area_px2 > 1.0
            decorated_overlaps.append(
                {
                    "axes": [
                        int(main_axes[first_index].number),
                        int(main_axes[second_index].number),
                    ],
                    "overlap_area_px2": area_px2,
                    "overlap": overlap,
                }
            )
            if overlap:
                failures.append(
                    f"Decorated bboxes overlap for Axes {main_axes[first_index].number} "
                    f"and {main_axes[second_index].number}."
                )

    map_frame, magnitude_frame, depth_frame = frame_boxes
    map_to_bottom_frame_gap_in = float(
        (map_frame.y0 - max(magnitude_frame.y1, depth_frame.y1)) / dpi
    )
    bottom_frame_gap_in = float((depth_frame.x0 - magnitude_frame.x1) / dpi)
    map_to_bottom_decorated_gap_in = float(
        (tight_boxes[0].y0 - max(tight_boxes[1].y1, tight_boxes[2].y1)) / dpi
    )
    bottom_decorated_gap_in = float((tight_boxes[2].x0 - tight_boxes[1].x1) / dpi)

    auxiliary_axes = [ax for ax in fig.axes if ax not in main_axes]
    auxiliary_checks = [
        {
            "classification": "auxiliary Axes",
            "type": type(ax).__name__,
            "visible_frame": bbox_dict(ax.get_window_extent(renderer), dpi),
            "decorated_tight_bbox": bbox_dict(ax.get_tightbbox(renderer), dpi),
        }
        for ax in auxiliary_axes
    ]

    if len(auxiliary_axes) != 1:
        failures.append(f"Detected {len(auxiliary_axes)} auxiliary Axes; expected one colorbar.")
    if axes_checks[0]["width_utilization"] < 0.8:
        failures.append("The dominant map uses less than 80% of its slot width.")
    if axes_checks[0]["height_utilization"] < 0.8:
        failures.append("The dominant map uses less than 80% of its slot height.")
    if map_to_bottom_decorated_gap_in < 0.0:
        failures.append("Map and lower-row decorated content overlap vertically.")
    if bottom_decorated_gap_in < 0.0:
        failures.append("Lower-row decorated content overlaps horizontally.")

    result = {
        "status": "pass" if not failures else "fail",
        "failures": failures,
        "scientific_question": (
            "Where did 2025 global M >= 5 earthquakes cluster, and what were their "
            "magnitude-frequency and depth-class characteristics?"
        ),
        "intended_message": (
            "Show global seismic belts, the dominance of M5 events, and the predominance "
            "of shallow earthquakes while retaining rarer large and deep events."
        ),
        "effective_ultraplot_rc_changed": dict(uplt.rc.changed),
        "sizing": {
            "width_authority": "journal=nat2",
            "expected_width_mm": EXPECTED_WIDTH_MM,
            "figure_width_in": fig_width_in,
            "figure_height_in": fig_height_in,
            "figure_width_mm": fig_width_in * 25.4,
            "figure_height_mm": fig_height_in * 25.4,
            "reference_subplot": 1,
            "reference_aspect_override": None,
            "export_dpi": EXPORT_DPI,
        },
        "layout": {
            "topology": [[1, 1], [2, 3]],
            "row_height_ratios": [1.65, 1.0],
            "manual_spacing_overrides": [],
            "map_to_bottom_frame_gap_in": map_to_bottom_frame_gap_in,
            "bottom_frame_gap_in": bottom_frame_gap_in,
            "map_to_bottom_decorated_gap_in": map_to_bottom_decorated_gap_in,
            "bottom_decorated_gap_in": bottom_decorated_gap_in,
            "decorated_bbox_overlaps": decorated_overlaps,
            "slot_frame_interpretation": (
                "All three main Axes have the same directional width utilization and "
                "full slot-height utilization. The width difference is classified as "
                "automatic decorated-content/outer-guide clearance, not a map-only "
                "fixed-aspect blank band."
            ),
        },
        "axes": axes_checks,
        "auxiliary_axes": auxiliary_checks,
        "outer_guides": {
            "depth_colorbar_axes_count": len(auxiliary_axes),
            "magnitude_legend_location": "upper-centre inside map over the sparsely occupied Arctic region",
            "magnitude_legend_bbox": bbox_dict(legend.get_window_extent(renderer), dpi),
        },
        "geospatial": {
            "source_coordinates": "validated WGS84 longitude-latitude display copy",
            "display_crs": "EPSG:4326 / Plate Carree",
            "display_extent_lon_lat": [-180.0, MAP_LATITUDE_LIMITS[0], 180.0, MAP_LATITUDE_LIMITS[1]],
            "coordinate_labels": "degree-formatted longitude on bottom and latitude on left",
            "north_south_orientation": "north-up",
            "raster_affine_resolution_nodata": "not applicable to point vector data",
            "basemap": "Cartopy coastline/land/ocean context through public UltraPlot formatting APIs; no basemap values enter analysis.",
        },
        "encodings_and_scoped_overrides": [
            "batlow sequential colormap and linear 0-650 km normalization for depth.",
            "Marker area = 11 + 30 * (M - 5) points squared; monotonic visual scale, not energy proportional.",
            "Magnitude marker transparency and thin white edges improve dense-point separation.",
            "Light-grey land is a map-only accessibility override because the effective black land fill obscured shallow-event batlow colours in the first render.",
            "Magnitude exceedance counts use a log y-axis; no bar or filled-area baseline is implied.",
            "Depth-class bars use a true zero baseline and colours sampled from the same depth colormap; white text is used only inside the dark shallow-event bar for contrast.",
            "Only the continuous colorbar solids are rasterized at the common 1000 dpi export resolution to suppress PDF gradient seams; map marks, axes, labels, and statistical panels remain vector.",
            "All typography, axes, ticks, gridline strokes, geographic labels, and guide text inherit the effective UltraPlot baseline.",
        ],
        "title_policy": {
            "authorized": False,
            "figure_level_title_present": False,
            "subplot_titles_present": False,
        },
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir", type=Path, default=Path(__file__).resolve().parent
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path(__file__).resolve().parent
    )
    args = parser.parse_args()
    data_dir = args.data_dir.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    events_path = data_dir / "earthquakes_2025_m5plus_processed.csv"
    exceedance_path = data_dir / "magnitude_exceedance.csv"
    depth_classes_path = data_dir / "depth_classes.csv"
    excluded_path = data_dir / "excluded_features.csv"
    required_files = [
        events_path,
        exceedance_path,
        depth_classes_path,
        excluded_path,
    ]
    for path in required_files:
        if not path.is_file():
            raise FileNotFoundError(path)

    events = read_csv(events_path)
    exceedance = read_csv(exceedance_path)
    depth_classes = read_csv(depth_classes_path)
    excluded = read_csv(excluded_path)

    longitude = np.asarray([float(row["longitude_deg"]) for row in events])
    latitude = np.asarray([float(row["latitude_deg"]) for row in events])
    depth = np.asarray([float(row["depth_km"]) for row in events])
    magnitude = np.asarray([float(row["magnitude"]) for row in events])
    thresholds = np.asarray(
        [float(row["magnitude_threshold"]) for row in exceedance]
    )
    exceedance_counts = np.asarray(
        [int(row["event_count_ge_threshold"]) for row in exceedance]
    )
    validate_processed_data(
        events,
        excluded,
        longitude,
        latitude,
        depth,
        magnitude,
        thresholds,
        exceedance_counts,
        depth_classes,
    )

    depth_vmax = float(math.ceil(depth.max() / 50.0) * 50.0)
    if depth_vmax != 650.0:
        raise ValueError(f"Expected a 650 km depth scale for this dataset; got {depth_vmax}.")
    depth_norm = Normalize(vmin=0.0, vmax=depth_vmax)
    depth_cmap = uplt.Colormap(DEPTH_CMAP)

    fig, axs = uplt.subplots(
        [[1, 1], [2, 3]],
        hratios=(1.65, 1.0),
        proj={1: "pcarree"},
        journal=JOURNAL_PRESET,
        refnum=1,
        share=False,
        span=False,
    )
    map_ax, magnitude_ax, depth_ax = axs

    order = np.argsort(magnitude, kind="stable")
    magnitude_sizes = marker_area(magnitude[order])
    earthquake_points = map_ax.scatter(
        longitude[order],
        latitude[order],
        c=depth[order],
        s=magnitude_sizes,
        cmap=depth_cmap,
        norm=depth_norm,
        transform=ccrs.PlateCarree(),
        alpha=0.72,
        edgecolors="white",
        linewidths=0.18,
        zorder=3,
    )

    magnitude_ax.plot(
        thresholds,
        exceedance_counts,
        marker="o",
        markersize=2.8,
        linewidth=1.3,
    )

    depth_names = [row["class_name"] for row in depth_classes]
    depth_ranges = [row["range_label"] for row in depth_classes]
    depth_counts = np.asarray([int(row["event_count"]) for row in depth_classes])
    depth_percents = np.asarray(
        [float(row["event_percent"]) for row in depth_classes]
    )
    class_medians = np.asarray(
        [float(row["median_depth_km"]) for row in depth_classes]
    )
    depth_y = np.asarray([2.0, 1.0, 0.0])
    class_colours = [depth_cmap(depth_norm(value)) for value in class_medians]
    depth_ax.barh(
        depth_y,
        depth_percents,
        color=class_colours,
        edgecolor="none",
    )

    axs.format(abc="a.", abcloc="ul")
    map_ax.format(
        lonlim=(-180.0, 180.0),
        latlim=MAP_LATITUDE_LIMITS,
        lonlocator=60,
        latlocator=30,
        lonlabels="b",
        latlabels="l",
        coast=True,
        land=True,
        landcolor="0.92",
        ocean=True,
        grid=True,
    )
    magnitude_ax.format(
        xlim=(5.0, 9.0),
        ylim=(0.8, 3000.0),
        xlocator=1.0,
        yscale="log",
        xlabel="Magnitude threshold M",
        ylabel=r"Events with magnitude $\geq M$",
        grid=True,
    )
    depth_ax.format(
        xlim=(0.0, 100.0),
        ylim=(-0.65, 2.9),
        xlocator=20.0,
        yticks=depth_y,
        yticklabels=[
            f"{name}\n{range_label.replace(' to ', '-')}"
            for name, range_label in zip(depth_names, depth_ranges)
        ],
        xlabel="Share of earthquakes (%)",
        grid=False,
    )

    depth_colorbar = map_ax.colorbar(
        earthquake_points,
        loc="r",
        label="Hypocentral depth (km)",
        ticks=[0.0, 70.0, 300.0, depth_vmax],
    )
    depth_colorbar.solids.set_edgecolor("none")
    depth_colorbar.solids.set_rasterized(True)
    legend_magnitudes = np.asarray([5.0, 6.0, 7.0, 8.0])
    legend_handles = [
        Line2D(
            [],
            [],
            linestyle="none",
            marker="o",
            markersize=float(np.sqrt(marker_area(value))),
            markerfacecolor="0.45",
            markeredgecolor="white",
            markeredgewidth=0.5,
        )
        for value in legend_magnitudes
    ]
    magnitude_legend = map_ax.legend(
        handles=legend_handles,
        labels=[f"M {value:.0f}" for value in legend_magnitudes],
        loc="uc",
        ncols=4,
        title="Magnitude",
    )

    magnitude_annotation = magnitude_ax.text(
        0.97,
        0.94,
        (
            f"Median M = {np.median(magnitude):.1f}\n"
            f"95th percentile = {np.quantile(magnitude, 0.95):.1f}"
        ),
        transform=magnitude_ax.transAxes,
        ha="right",
        va="top",
    )
    depth_annotations = []
    for y_value, count, percent in zip(depth_y, depth_counts, depth_percents):
        inside_bar = percent > 60.0
        depth_annotations.append(
            depth_ax.text(
                float(percent - 1.5 if inside_bar else percent + 1.2),
                float(y_value),
                f"{count:,} ({percent:.1f}%)",
                ha="right" if inside_bar else "left",
                va="center",
                color="white" if inside_bar else None,
            )
        )

    annotations = {
        "a.": [magnitude_legend],
        "b.": [magnitude_annotation],
        "c.": depth_annotations,
    }
    layout_check = validate_layout(
        fig,
        [map_ax, magnitude_ax, depth_ax],
        annotations,
        magnitude_legend,
    )
    if layout_check["status"] != "pass":
        raise RuntimeError(
            "Figure layout validation failed: " + "; ".join(layout_check["failures"])
        )

    pdf_path = output_dir / "earthquakes_2025_m5plus_global.pdf"
    png_path = output_dir / "earthquakes_2025_m5plus_global.png"
    fig.save(pdf_path, dpi=EXPORT_DPI, metadata=PDF_METADATA)
    fig.save(png_path, dpi=EXPORT_DPI, metadata=PNG_METADATA)

    print(
        json.dumps(
            {
                "status": layout_check["status"],
                "figure_size_in": [
                    layout_check["sizing"]["figure_width_in"],
                    layout_check["sizing"]["figure_height_in"],
                ],
                "pdf": pdf_path.name,
                "png": png_path.name,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
