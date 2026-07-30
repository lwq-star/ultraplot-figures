"""Create the publication correlation scatter figure with UltraPlot."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

from matplotlib.text import Text
from matplotlib.transforms import Bbox
import numpy as np
import pandas as pd
import ultraplot as uplt


EXPORT_DPI = 1000
LAND_COVERS = ("cropland", "forest", "grassland", "savanna")
LAND_LABELS = {
    "cropland": "Cropland",
    "forest": "Forest",
    "grassland": "Grassland",
    "savanna": "Savanna",
}
MODELS = ("DNN", "GBRT", "LR", "SVR")
EXPECTED_IDENTIFIERS = ("a.", "b.", "c.", "d.")
OUTPUT_ROOT = Path(__file__).resolve().parent
DEFAULT_DATA = OUTPUT_ROOT / "processed_pairs.csv"
DEFAULT_STATISTICS = OUTPUT_ROOT / "correlation_statistics.csv"
DEFAULT_FIGURE_DIR = OUTPUT_ROOT
PDF_METADATA = {
    "Creator": "UltraPlot",
    "Producer": "UltraPlot",
    "CreationDate": None,
}
PNG_METADATA = {"Software": "UltraPlot"}


def visible_text_bbox(text: Text, renderer: object) -> Bbox:
    parts = [text.get_window_extent(renderer)]
    patch = text.get_bbox_patch()
    if patch is not None and patch.get_visible():
        parts.append(patch.get_window_extent(renderer))
    return Bbox.union(parts)


def bbox_record(bbox: Bbox, fig: object) -> dict[str, list[float]]:
    bbox_in = bbox.transformed(fig.dpi_scale_trans.inverted())
    return {
        "pixels": [float(value) for value in bbox.extents],
        "inches": [float(value) for value in bbox_in.extents],
        "size_inches": [float(bbox_in.width), float(bbox_in.height)],
    }


def bbox_inside(inner: Bbox, outer: Bbox, tolerance_px: float = 1.0) -> bool:
    return bool(
        inner.x0 >= outer.x0 - tolerance_px
        and inner.y0 >= outer.y0 - tolerance_px
        and inner.x1 <= outer.x1 + tolerance_px
        and inner.y1 <= outer.y1 + tolerance_px
    )


def intersection_area(first: Bbox, second: Bbox) -> float:
    intersection = Bbox.intersection(first, second)
    if intersection is None:
        return 0.0
    return float(max(0.0, intersection.width) * max(0.0, intersection.height))


def shared_limits(data: pd.DataFrame) -> tuple[float, float]:
    minimum = float(data[["value_0", "value_1"]].min().min())
    maximum = float(data[["value_0", "value_1"]].max().max())
    span = maximum - minimum
    if not np.isfinite(span) or span <= 0:
        raise ValueError("Cannot derive finite shared limits from the processed data.")
    padding = 0.025 * span
    magnitude = 10 ** math.floor(math.log10(span))
    rounding = magnitude / 20.0
    lower = math.floor((minimum - padding) / rounding) * rounding
    upper = math.ceil((maximum + padding) / rounding) * rounding
    return float(lower), float(upper)


def validate_inputs(data: pd.DataFrame, statistics: pd.DataFrame) -> None:
    expected_data_columns = {
        "source_sheet",
        "source_excel_row",
        "land_cover",
        "model",
        "value_0",
        "value_1",
    }
    if set(data.columns) != expected_data_columns:
        raise ValueError(f"Unexpected processed-data columns: {list(data.columns)!r}")
    if data[["value_0", "value_1"]].isna().any().any():
        raise ValueError("Processed data contain missing plotted values.")
    if not np.isfinite(data[["value_0", "value_1"]].to_numpy()).all():
        raise ValueError("Processed data contain non-finite plotted values.")
    expected_pairs = {(land, model) for land in LAND_COVERS for model in MODELS}
    actual_pairs = set(zip(data["land_cover"], data["model"]))
    if actual_pairs != expected_pairs:
        raise ValueError("Processed data do not contain exactly the 16 expected groups.")
    stats_pairs = set(zip(statistics["land_cover"], statistics["model"]))
    if stats_pairs != expected_pairs or len(statistics) != len(expected_pairs):
        raise ValueError("Statistics table does not contain exactly the 16 expected rows.")


def build_figure(data: pd.DataFrame, statistics: pd.DataFrame):
    limits = shared_limits(data)
    colors = uplt.Cycle("colorblind").by_key()["color"][: len(MODELS)]
    model_colors = dict(zip(MODELS, colors))

    fig, axs = uplt.subplots(
        nrows=2,
        ncols=2,
        journal="nat2",
        refaspect=1,
    )

    regression_handles = []
    reference_handle = None
    for panel_index, (land_cover, ax) in enumerate(zip(LAND_COVERS, axs)):
        reference = ax.plot(
            limits,
            limits,
            color="0.45",
            linewidth=0.9,
            linestyle="--",
            zorder=0,
            label="1:1 reference",
        )[0]
        if reference_handle is None:
            reference_handle = reference

        for model in MODELS:
            subset = data[
                (data["land_cover"] == land_cover) & (data["model"] == model)
            ]
            ax.scatter(
                subset["value_0"],
                subset["value_1"],
                s=4.0,
                marker="o",
                color=model_colors[model],
                alpha=0.16,
                edgecolors="none",
                rasterized=True,
                zorder=1,
            )
            stat_row = statistics[
                (statistics["land_cover"] == land_cover)
                & (statistics["model"] == model)
            ].iloc[0]
            x_line = np.asarray([stat_row["x_min"], stat_row["x_max"]])
            y_line = stat_row["ols_intercept"] + stat_row["ols_slope"] * x_line
            line = ax.plot(
                x_line,
                y_line,
                color=model_colors[model],
                linewidth=1.2,
                zorder=2,
                label=model,
            )[0]
            if panel_index == 0:
                regression_handles.append(line)

    axs.format(
        abc="a.",
        abcloc="ul",
        xlabel="Value (_0)",
        ylabel="Value (_1)",
        xlim=limits,
        ylim=limits,
        aspect="equal",
        grid=False,
    )

    annotation_handles: dict[str, list[Text]] = {}
    annotation_box = {
        "boxstyle": "square,pad=0.22",
        "facecolor": "white",
        "edgecolor": "none",
        "alpha": 0.84,
    }
    for land_cover, ax in zip(LAND_COVERS, axs):
        land_statistics = statistics[statistics["land_cover"] == land_cover]
        n_values = land_statistics["n"].astype(int).unique()
        if len(n_values) != 1:
            raise ValueError(f"Model sample counts differ for {land_cover}.")
        land_text = ax.text(
            0.97,
            0.965,
            f"{LAND_LABELS[land_cover]} | n = {n_values[0]:,}",
            transform=ax.transAxes,
            ha="right",
            va="top",
            bbox=annotation_box,
            zorder=4,
        )
        r_lines = []
        for model in MODELS:
            row = land_statistics[land_statistics["model"] == model].iloc[0]
            r_lines.append(f"{model}: r = {row['pearson_r']:.3f}")
        stats_text = ax.text(
            0.97,
            0.035,
            "\n".join(r_lines),
            transform=ax.transAxes,
            ha="right",
            va="bottom",
            bbox=annotation_box,
            zorder=4,
        )
        annotation_handles[land_cover] = [land_text, stats_text]

    legend = fig.legend(
        [*regression_handles, reference_handle],
        loc="b",
        ncols=5,
        frame=False,
        center=True,
    )
    return fig, axs, legend, annotation_handles, limits, model_colors


def audit_figure(
    fig: object,
    axs: object,
    legend: object,
    annotation_handles: dict[str, list[Text]],
    limits: tuple[float, float],
    model_colors: dict[str, str],
) -> dict[str, object]:
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    canvas_width, canvas_height = fig.canvas.get_width_height()
    canvas = Bbox.from_bounds(0.0, 0.0, float(canvas_width), float(canvas_height))
    figure_width_in, figure_height_in = map(float, fig.get_size_inches())
    axes_audit: list[dict[str, object]] = []
    tight_boxes: list[Bbox] = []
    frame_boxes: list[Bbox] = []
    all_identifier_checks: list[bool] = []
    all_containment_checks: list[bool] = []
    all_annotation_clearance_checks: list[bool] = []
    all_title_checks: list[bool] = []

    for land_cover, expected_identifier, ax in zip(
        LAND_COVERS, EXPECTED_IDENTIFIERS, axs
    ):
        slot_norm = ax.get_subplotspec().get_position(fig)
        slot = Bbox.from_extents(
            slot_norm.x0 * canvas_width,
            slot_norm.y0 * canvas_height,
            slot_norm.x1 * canvas_width,
            slot_norm.y1 * canvas_height,
        )
        frame = ax.get_window_extent(renderer)
        tight = ax.get_tightbbox(renderer)
        frame_boxes.append(frame)
        tight_boxes.append(tight)

        matches = [
            text
            for text in ax.findobj(match=Text)
            if text.get_visible() and text.get_text() == expected_identifier
        ]
        identifier_count_ok = len(matches) == 1
        identifier_record: dict[str, object] = {
            "expected": expected_identifier,
            "detected_count": len(matches),
        }
        identifier_in_upper_left = False
        identifier_inside_frame = False
        identifier_inside_canvas = False
        annotation_clear = False
        annotation_records = []
        if identifier_count_ok:
            identifier_bbox = visible_text_bbox(matches[0], renderer)
            clearance_px = 2.0 * fig.dpi / 72.0
            reserved_bbox = Bbox.from_extents(
                identifier_bbox.x0 - clearance_px,
                identifier_bbox.y0 - clearance_px,
                identifier_bbox.x1 + clearance_px,
                identifier_bbox.y1 + clearance_px,
            )
            center_x = 0.5 * (identifier_bbox.x0 + identifier_bbox.x1)
            center_y = 0.5 * (identifier_bbox.y0 + identifier_bbox.y1)
            identifier_in_upper_left = bool(
                center_x <= frame.x0 + 0.30 * frame.width
                and center_y >= frame.y0 + 0.70 * frame.height
            )
            identifier_inside_frame = bbox_inside(identifier_bbox, frame, 1.0)
            identifier_inside_canvas = bbox_inside(identifier_bbox, canvas, 1.0)
            overlaps = []
            for annotation in annotation_handles[land_cover]:
                annotation_bbox = visible_text_bbox(annotation, renderer)
                overlap_area = intersection_area(reserved_bbox, annotation_bbox)
                overlaps.append(overlap_area)
                annotation_records.append(
                    {
                        "text": annotation.get_text(),
                        "bbox": bbox_record(annotation_bbox, fig),
                        "inside_visible_frame": bbox_inside(
                            annotation_bbox, frame, 1.0
                        ),
                        "identifier_reserved_overlap_px2": overlap_area,
                    }
                )
            annotation_clear = all(area <= 0.5 for area in overlaps)
            identifier_record.update(
                {
                    "bbox": bbox_record(identifier_bbox, fig),
                    "reserved_bbox": bbox_record(reserved_bbox, fig),
                    "inside_upper_left_region": identifier_in_upper_left,
                    "inside_visible_frame": identifier_inside_frame,
                    "inside_canvas": identifier_inside_canvas,
                }
            )

        titles = {loc: ax.get_title(loc=loc) for loc in ("left", "center", "right")}
        title_free = not any(titles.values())
        slot_width_in = float(slot_norm.width * figure_width_in)
        slot_height_in = float(slot_norm.height * figure_height_in)
        frame_in = frame.transformed(fig.dpi_scale_trans.inverted())
        tight_in = tight.transformed(fig.dpi_scale_trans.inverted())
        frame_width_in = float(frame_in.width)
        frame_height_in = float(frame_in.height)
        aspect_value = ax.get_aspect()
        fixed_aspect = aspect_value != "auto"
        axes_audit.append(
            {
                "land_cover": land_cover,
                "axes_number": int(ax.number),
                "expected_identifier": expected_identifier,
                "slot": bbox_record(slot, fig),
                "visible_frame": bbox_record(frame, fig),
                "tight_boundary": bbox_record(tight, fig),
                "slot_size_inches": [slot_width_in, slot_height_in],
                "visible_frame_size_inches": [frame_width_in, frame_height_in],
                "tight_size_inches": [float(tight_in.width), float(tight_in.height)],
                "slot_utilization": {
                    "width": frame_width_in / slot_width_in,
                    "height": frame_height_in / slot_height_in,
                },
                "aspect": str(aspect_value),
                "fixed_aspect": fixed_aspect,
                "tight_boundary_inside_canvas": bbox_inside(tight, canvas, 1.0),
                "titles": titles,
                "title_free": title_free,
                "identifier": identifier_record,
                "ordinary_annotations": annotation_records,
            }
        )
        all_identifier_checks.append(
            identifier_count_ok
            and identifier_in_upper_left
            and identifier_inside_frame
            and identifier_inside_canvas
        )
        all_containment_checks.append(bbox_inside(tight, canvas, 1.0))
        all_annotation_clearance_checks.append(annotation_clear)
        all_title_checks.append(title_free)

    decorated_overlaps = []
    for left_index in range(len(tight_boxes)):
        for right_index in range(left_index + 1, len(tight_boxes)):
            area = intersection_area(tight_boxes[left_index], tight_boxes[right_index])
            decorated_overlaps.append(
                {
                    "axes_numbers": [left_index + 1, right_index + 1],
                    "intersection_area_px2": area,
                }
            )

    horizontal_gaps = []
    for first, second in ((0, 1), (2, 3)):
        horizontal_gaps.append(
            {
                "axes_numbers": [first + 1, second + 1],
                "frame_gap_inches": float(
                    (frame_boxes[second].x0 - frame_boxes[first].x1) / fig.dpi
                ),
                "decorated_gap_inches": float(
                    (tight_boxes[second].x0 - tight_boxes[first].x1) / fig.dpi
                ),
            }
        )
    vertical_gaps = []
    for top, bottom in ((0, 2), (1, 3)):
        vertical_gaps.append(
            {
                "axes_numbers": [top + 1, bottom + 1],
                "frame_gap_inches": float(
                    (frame_boxes[top].y0 - frame_boxes[bottom].y1) / fig.dpi
                ),
                "decorated_gap_inches": float(
                    (tight_boxes[top].y0 - tight_boxes[bottom].y1) / fig.dpi
                ),
            }
        )

    legend_bbox = legend.get_window_extent(renderer)
    legend_overlap_areas = [
        intersection_area(legend_bbox, tight_bbox) for tight_bbox in tight_boxes
    ]
    figure_suptitle = fig.get_suptitle()
    axes_numbers = [int(ax.number) for ax in axs]
    frame_sizes_ok = all(
        min(record["visible_frame_size_inches"]) >= 2.2 for record in axes_audit
    )
    utilization_ok = all(
        record["slot_utilization"]["width"] >= 0.90
        and record["slot_utilization"]["height"] >= 0.90
        for record in axes_audit
    )
    rc_changes = {str(key): repr(value) for key, value in uplt.rc.changed.items()}
    checks = {
        "four_independent_main_axes": len(axs) == 4,
        "row_major_axes_numbers_1_to_4": axes_numbers == [1, 2, 3, 4],
        "identifier_count_location_and_containment": all(all_identifier_checks),
        "identifier_reserved_regions_clear": all(all_annotation_clearance_checks),
        "main_axes_tight_boundaries_inside_canvas": all(all_containment_checks),
        "no_subplot_titles": all(all_title_checks),
        "no_figure_title": not bool(figure_suptitle),
        "adjacent_decorated_boundaries_do_not_overlap": all(
            item["intersection_area_px2"] <= 0.5 for item in decorated_overlaps
        ),
        "outer_legend_inside_canvas": bbox_inside(legend_bbox, canvas, 1.0),
        "outer_legend_clear_of_main_axes": all(
            area <= 0.5 for area in legend_overlap_areas
        ),
        "fixed_aspect_frame_sizes_readable": frame_sizes_ok,
        "fixed_aspect_slot_utilization_acceptable": utilization_ok,
        "in_memory_nat2_width_within_0_2_mm": abs(
            figure_width_in * 25.4 - 183.0
        )
        <= 0.2,
        "rc_changes_explained": len(rc_changes) == 0,
        "export_dpi_above_600": EXPORT_DPI > 600,
    }
    audit = {
        "passed": all(checks.values()),
        "checks": checks,
        "size_authority": "journal=nat2",
        "figure_size": {
            "inches": [figure_width_in, figure_height_in],
            "millimetres": [figure_width_in * 25.4, figure_height_in * 25.4],
        },
        "export_dpi": EXPORT_DPI,
        "shared_axis_limits": list(limits),
        "main_axes_count": len(axs),
        "auxiliary_axes_count": max(0, len(fig.axes) - len(axs)),
        "axes_numbers": axes_numbers,
        "expected_identifiers": list(EXPECTED_IDENTIFIERS),
        "axes": axes_audit,
        "decorated_boundary_intersections": decorated_overlaps,
        "measured_frame_gaps": {
            "horizontal": horizontal_gaps,
            "vertical": vertical_gaps,
        },
        "outer_legend": {
            "bbox": bbox_record(legend_bbox, fig),
            "inside_canvas": bbox_inside(legend_bbox, canvas, 1.0),
            "main_axes_overlap_px2": legend_overlap_areas,
        },
        "figure_suptitle": figure_suptitle,
        "model_colors": model_colors,
        "effective_rc_changes": rc_changes,
        "manual_spacing_overrides": [],
        "style_overrides": [
            "UltraPlot colorblind categorical cycle for model identity.",
            "Small alpha=0.16 rasterized points to reveal dense clouds while keeping the PDF tractable.",
            "Per-model OLS lines limited to each group's observed x range, plus a neutral dashed 1:1 reference.",
            "Equal x/y limits and equal aspect so the 1:1 reference is geometrically honest.",
            "Semi-transparent white square annotation backing to keep statistics legible over dense points.",
            "Figure-local abc='a.' and abcloc='ul' as required by the skill.",
            "Figure-local grid=False because gridlines do not aid this dense comparison.",
        ],
    }
    return audit


def plot(
    data_path: Path,
    statistics_path: Path,
    figure_dir: Path,
) -> None:
    data_path = data_path.resolve(strict=True)
    statistics_path = statistics_path.resolve(strict=True)
    figure_dir.mkdir(parents=True, exist_ok=True)

    data = pd.read_csv(data_path)
    statistics = pd.read_csv(statistics_path)
    validate_inputs(data, statistics)

    fig, axs, legend, annotations, limits, model_colors = build_figure(
        data, statistics
    )
    pdf_path = figure_dir / "correlation_scatter.pdf"
    png_path = figure_dir / "correlation_scatter.png"
    fig.save(pdf_path, dpi=EXPORT_DPI, metadata=PDF_METADATA)
    fig.save(png_path, dpi=EXPORT_DPI, metadata=PNG_METADATA)

    audit = audit_figure(
        fig,
        axs,
        legend,
        annotations,
        limits,
        model_colors,
    )
    uplt.close(fig)

    if pdf_path.stat().st_size == 0 or png_path.stat().st_size == 0:
        raise RuntimeError("One or more figure outputs are empty.")

    print(f"Figure size: {audit['figure_size']['millimetres']} mm")
    print(f"Shared limits: {audit['shared_axis_limits']}")
    print(f"Wrote: {pdf_path.name}")
    print(f"Wrote: {png_path.name}")
    if not audit["passed"]:
        failed = [name for name, passed in audit["checks"].items() if not passed]
        raise RuntimeError(f"Figure audit failed: {failed}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--statistics", type=Path, default=DEFAULT_STATISTICS)
    parser.add_argument("--figure-dir", type=Path, default=DEFAULT_FIGURE_DIR)
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    plot(
        arguments.data,
        arguments.statistics,
        arguments.figure_dir,
    )
