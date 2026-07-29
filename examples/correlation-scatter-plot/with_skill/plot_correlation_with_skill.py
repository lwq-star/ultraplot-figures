from __future__ import annotations

import json
import math
import os
from pathlib import Path

import cartopy
import matplotlib
from matplotlib.text import Text
import numpy as np
import pandas as pd
from PIL import Image
from pypdf import PdfReader
from pypdf.generic import ContentStream
import ultraplot as uplt


EXPORT_DPI = 1000
LAND_COVERS = ("cropland", "forest", "grassland", "savanna")
LAND_COVER_LABELS = ("Cropland", "Forest", "Grassland", "Savanna")
MODELS = ("DNN", "GBRT", "LR", "SVR")

OUTPUT_DIR = Path(__file__).resolve().parent
PAIRS_PATH = OUTPUT_DIR / "correlation_pairs_with_skill.csv"
STATS_PATH = OUTPUT_DIR / "correlation_stats_with_skill.csv"
PDF_PATH = OUTPUT_DIR / "correlation_scatter_with_skill.pdf"
PNG_PATH = OUTPUT_DIR / "correlation_scatter_with_skill.png"
VERIFICATION_PATH = OUTPUT_DIR / "verification_with_skill.json"


def report_relative_path(path: Path, report_path: Path) -> str:
    return Path(os.path.relpath(path, start=report_path.parent)).as_posix()


def normalized_bbox_inches(bbox, figure_width: float, figure_height: float) -> dict[str, float]:
    return {
        "x0": float(bbox.x0 * figure_width),
        "y0": float(bbox.y0 * figure_height),
        "x1": float(bbox.x1 * figure_width),
        "y1": float(bbox.y1 * figure_height),
        "width": float(bbox.width * figure_width),
        "height": float(bbox.height * figure_height),
    }


def display_bbox_inches(bbox, figure_dpi: float) -> dict[str, float]:
    return {
        "x0": float(bbox.x0 / figure_dpi),
        "y0": float(bbox.y0 / figure_dpi),
        "x1": float(bbox.x1 / figure_dpi),
        "y1": float(bbox.y1 / figure_dpi),
        "width": float(bbox.width / figure_dpi),
        "height": float(bbox.height / figure_dpi),
    }


def main() -> None:
    pairs = pd.read_csv(PAIRS_PATH)
    stats = pd.read_csv(STATS_PATH)

    expected_pair_columns = [
        "land_cover", "model", "source_row", "value_0", "value_1"
    ]
    expected_stats_columns = [
        "land_cover",
        "model",
        "n",
        "pearson_r",
        "ols_slope",
        "ols_intercept",
        "x_min",
        "x_max",
        "y_min",
        "y_max",
    ]
    if pairs.columns.tolist() != expected_pair_columns:
        raise ValueError("Processed pair-table columns differ from expectation.")
    if stats.columns.tolist() != expected_stats_columns:
        raise ValueError("Processed statistics-table columns differ from expectation.")
    if not np.isfinite(pairs[["value_0", "value_1"]].to_numpy()).all():
        raise ValueError("Processed pair table contains non-finite values.")

    observed_groups = set(zip(pairs["land_cover"], pairs["model"]))
    expected_groups = {(land, model) for land in LAND_COVERS for model in MODELS}
    if observed_groups != expected_groups:
        raise ValueError("Processed pair table does not contain the expected 16 groups.")
    if set(zip(stats["land_cover"], stats["model"])) != expected_groups:
        raise ValueError("Statistics table does not contain the expected 16 groups.")

    values = pairs[["value_0", "value_1"]].to_numpy(dtype=float)
    data_min = float(values.min())
    data_max = float(values.max())
    tick_scale = 10.0
    padding = 0.02 * (data_max - data_min)
    limit_min = tick_scale * math.floor((data_min - padding) / tick_scale)
    limit_max = tick_scale * math.ceil((data_max + padding) / tick_scale)

    rc_changed_before = dict(uplt.rc.changed)
    row_colors = uplt.Cycle("colorblind").by_key()["color"][: len(LAND_COVERS)]

    fig, axs = uplt.subplots(
        nrows=4,
        ncols=4,
        journal="nat2",
        share=True,
        span=True,
    )

    stats_indexed = stats.set_index(["land_cover", "model"])
    identity_handle = None
    fit_handle = None
    annotation_artists: list[Text] = []
    for row, land_cover in enumerate(LAND_COVERS):
        for column, model in enumerate(MODELS):
            ax = axs[row, column]
            group = pairs[
                (pairs["land_cover"] == land_cover) & (pairs["model"] == model)
            ]
            summary = stats_indexed.loc[(land_cover, model)]
            x = group["value_0"].to_numpy(dtype=float)
            y = group["value_1"].to_numpy(dtype=float)

            identity = ax.plot(
                [limit_min, limit_max],
                [limit_min, limit_max],
                color="0.50",
                linestyle="--",
                linewidth=0.8,
                label="1:1 reference",
                zorder=1,
            )[0]
            ax.scatter(
                x,
                y,
                s=3.5,
                color=row_colors[row],
                alpha=0.18,
                edgecolors="none",
                rasterized=True,
                zorder=2,
            )
            x_fit = np.array([summary["x_min"], summary["x_max"]], dtype=float)
            y_fit = summary["ols_intercept"] + summary["ols_slope"] * x_fit
            fitted = ax.plot(
                x_fit,
                y_fit,
                color="black",
                linewidth=1.0,
                label="OLS fit",
                zorder=3,
            )[0]
            annotation = ax.text(
                0.04,
                0.96,
                rf"$r$ = {summary['pearson_r']:.3f}; $n$ = {int(summary['n']):,}",
                transform=ax.transAxes,
                ha="left",
                va="top",
                fontsize="small",
                bbox={
                    "facecolor": "white",
                    "edgecolor": "none",
                    "alpha": 0.78,
                    "pad": 0.8,
                },
                zorder=4,
            )
            annotation_artists.append(annotation)
            if row == 0 and column == 0:
                identity_handle = identity
                fit_handle = fitted

    axs.format(
        xlim=(limit_min, limit_max),
        ylim=(limit_min, limit_max),
        xlabel="_0 value",
        ylabel="_1 value",
        aspect="equal",
        grid=False,
    )
    fig.format(toplabels=MODELS, leftlabels=LAND_COVER_LABELS)
    shared_legend = fig.legend(
        [identity_handle, fit_handle],
        loc="b",
        ncols=2,
        center=True,
    )

    if fig.get_suptitle():
        raise RuntimeError("A figure-level title was created unexpectedly.")
    for ax in axs:
        if any(ax.get_title(loc=loc) for loc in ("left", "center", "right")):
            raise RuntimeError("A subplot title was created unexpectedly.")

    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    figure_width, figure_height = (float(value) for value in fig.get_size_inches())
    figure_dpi = float(fig.dpi)
    canvas_tolerance_inches = 2.0 / figure_dpi

    axes_geometry: list[dict[str, object]] = []
    decorated_boxes: dict[tuple[int, int], dict[str, float]] = {}
    all_axes_contained = True
    for row, land_cover in enumerate(LAND_COVERS):
        for column, model in enumerate(MODELS):
            ax = axs[row, column]
            slot = normalized_bbox_inches(
                ax.get_subplotspec().get_position(fig), figure_width, figure_height
            )
            visible = normalized_bbox_inches(
                ax.get_position(), figure_width, figure_height
            )
            decorated = display_bbox_inches(ax.get_tightbbox(renderer), figure_dpi)
            decorated_boxes[(row, column)] = decorated
            contained = (
                decorated["x0"] >= -canvas_tolerance_inches
                and decorated["y0"] >= -canvas_tolerance_inches
                and decorated["x1"] <= figure_width + canvas_tolerance_inches
                and decorated["y1"] <= figure_height + canvas_tolerance_inches
            )
            all_axes_contained = all_axes_contained and contained
            axes_geometry.append(
                {
                    "land_cover": land_cover,
                    "model": model,
                    "grid_slot_inches": slot,
                    "visible_frame_inches": visible,
                    "decorated_bbox_inches": decorated,
                    "decorated_bbox_inside_canvas": contained,
                }
            )

    horizontal_decorated_gaps: list[float] = []
    for row in range(4):
        for column in range(3):
            left = decorated_boxes[(row, column)]
            right = decorated_boxes[(row, column + 1)]
            horizontal_decorated_gaps.append(float(right["x0"] - left["x1"]))

    vertical_decorated_gaps: list[float] = []
    for row in range(3):
        for column in range(4):
            upper = decorated_boxes[(row, column)]
            lower = decorated_boxes[(row + 1, column)]
            vertical_decorated_gaps.append(float(upper["y0"] - lower["y1"]))

    semantic_text = {
        *MODELS,
        *LAND_COVER_LABELS,
        "_0 value",
        "_1 value",
        "1:1 reference",
        "OLS fit",
    }
    relevant_text_artists: list[Text] = list(annotation_artists)
    relevant_text_artists.extend(
        text_artist
        for text_artist in fig.findobj(match=Text)
        if text_artist.get_text() in semantic_text
    )
    if hasattr(shared_legend, "get_texts"):
        relevant_text_artists.extend(shared_legend.get_texts())
    for ax in axs:
        x_min, x_max = sorted(ax.get_xlim())
        y_min, y_max = sorted(ax.get_ylim())
        relevant_text_artists.extend(
            label
            for value, label in zip(ax.get_xticks(), ax.get_xticklabels())
            if x_min <= value <= x_max and label.get_visible()
        )
        relevant_text_artists.extend(
            label
            for value, label in zip(ax.get_yticks(), ax.get_yticklabels())
            if y_min <= value <= y_max and label.get_visible()
        )

    text_outside_canvas: list[dict[str, object]] = []
    checked_text_ids: set[int] = set()
    for text_artist in relevant_text_artists:
        if (
            id(text_artist) in checked_text_ids
            or not text_artist.get_visible()
            or not text_artist.get_text().strip()
        ):
            continue
        checked_text_ids.add(id(text_artist))
        bbox = display_bbox_inches(text_artist.get_window_extent(renderer), figure_dpi)
        if (
            bbox["x0"] < -canvas_tolerance_inches
            or bbox["y0"] < -canvas_tolerance_inches
            or bbox["x1"] > figure_width + canvas_tolerance_inches
            or bbox["y1"] > figure_height + canvas_tolerance_inches
        ):
            text_outside_canvas.append(
                {"text": text_artist.get_text(), "bbox_inches": bbox}
            )

    rc_changed_after_render = dict(uplt.rc.changed)
    fig.save(PDF_PATH, dpi=EXPORT_DPI)
    fig.save(PNG_PATH, dpi=EXPORT_DPI)

    pdf_reader = PdfReader(PDF_PATH)
    if len(pdf_reader.pages) != 1:
        raise RuntimeError("Expected a one-page PDF output.")
    pdf_page = pdf_reader.pages[0]
    pdf_width_points = float(pdf_page.mediabox.width)
    pdf_height_points = float(pdf_page.mediabox.height)
    pdf_width_mm = pdf_width_points * 25.4 / 72.0
    pdf_height_mm = pdf_height_points * 25.4 / 72.0

    required_pdf_text = [
        *MODELS,
        *LAND_COVER_LABELS,
        "_0 value",
        "_1 value",
        "1:1 reference",
        "OLS fit",
    ]
    extracted_pdf_text = pdf_page.extract_text()
    pdf_required_text_present = {
        label: label in extracted_pdf_text for label in required_pdf_text
    }

    xobjects = pdf_page["/Resources"]["/XObject"].get_object()
    image_dimensions: dict[str, tuple[int, int]] = {}
    for name, reference in xobjects.items():
        xobject = reference.get_object()
        if xobject.get("/Subtype") == "/Image":
            image_dimensions[str(name)] = (
                int(xobject["/Width"]),
                int(xobject["/Height"]),
            )

    pdf_raster_layers: list[dict[str, object]] = []
    content = ContentStream(pdf_page.get_contents(), pdf_reader)
    for index, (operands, operator) in enumerate(content.operations):
        if operator != b"Do" or str(operands[0]) not in image_dimensions:
            continue
        if index == 0 or content.operations[index - 1][1] != b"cm":
            raise RuntimeError("PDF raster layer has no direct placement matrix.")
        matrix = [float(value) for value in content.operations[index - 1][0]]
        a, b, c, d, _, _ = matrix
        placed_width_points = math.hypot(a, b)
        placed_height_points = math.hypot(c, d)
        pixel_width, pixel_height = image_dimensions[str(operands[0])]
        dpi_x = pixel_width * 72.0 / placed_width_points
        dpi_y = pixel_height * 72.0 / placed_height_points
        pdf_raster_layers.append(
            {
                "name": str(operands[0]),
                "pixels": [pixel_width, pixel_height],
                "placed_points": [placed_width_points, placed_height_points],
                "effective_dpi": [dpi_x, dpi_y],
            }
        )

    pdf_raster_dpi_values = [
        dpi
        for layer in pdf_raster_layers
        for dpi in layer["effective_dpi"]
    ]
    pdf_raster_dpi_matches = (
        len(pdf_raster_layers) == 16
        and all(abs(dpi - EXPORT_DPI) <= 1.5 for dpi in pdf_raster_dpi_values)
    )

    with Image.open(PNG_PATH) as image:
        png_pixels = [int(image.width), int(image.height)]
        png_dpi_metadata = [float(value) for value in image.info.get("dpi", (0, 0))]

    expected_png_pixels = [
        int(round(figure_width * EXPORT_DPI)),
        int(round(figure_height * EXPORT_DPI)),
    ]
    png_dimensions_match = all(
        abs(actual - expected) <= 1
        for actual, expected in zip(png_pixels, expected_png_pixels)
    )
    png_dpi_matches = all(
        abs(actual - EXPORT_DPI) <= 0.1 for actual in png_dpi_metadata
    )
    pdf_width_matches_nat2 = abs(pdf_width_mm - 183.0) <= 0.2
    pdf_canvas_matches_figure = (
        abs(pdf_width_points / 72.0 - figure_width) <= 0.001
        and abs(pdf_height_points / 72.0 - figure_height) <= 0.001
    )
    decorated_nonoverlap = (
        min(horizontal_decorated_gaps) >= -canvas_tolerance_inches
        and min(vertical_decorated_gaps) >= -canvas_tolerance_inches
    )
    rc_context_did_not_leak = rc_changed_before == rc_changed_after_render

    passed = all(
        [
            EXPORT_DPI > 600,
            all_axes_contained,
            not text_outside_canvas,
            decorated_nonoverlap,
            pdf_width_matches_nat2,
            pdf_canvas_matches_figure,
            all(pdf_required_text_present.values()),
            pdf_raster_dpi_matches,
            png_dimensions_match,
            png_dpi_matches,
            rc_context_did_not_leak,
        ]
    )

    verification = {
        "path_base": "directory_containing_this_json",
        "passed": passed,
        "environment": {
            "ultraplot": uplt.__version__,
            "matplotlib": matplotlib.__version__,
            "cartopy": cartopy.__version__,
        },
        "scientific_question": (
            "How does the paired _0-to-_1 linear relationship vary across four "
            "land-cover classes and four model families?"
        ),
        "intended_message": (
            "Readers can compare point dispersion, Pearson correlation, OLS trend, "
            "and departure from the 1:1 reference across all 16 combinations."
        ),
        "data_policy": {
            "raw_pairs_plotted": True,
            "pairwise_complete_observations_only": True,
            "filtering_or_outlier_removal": False,
            "aggregation": False,
            "units_invented": False,
            "axis_labels": ["_0 value", "_1 value"],
            "global_data_min": data_min,
            "global_data_max": data_max,
            "shared_limits": [limit_min, limit_max],
        },
        "layout": {
            "topology": "regular 4-row by 4-column grid",
            "row_structure": list(LAND_COVER_LABELS),
            "column_structure": list(MODELS),
            "shared_limits": True,
            "equal_data_aspect": True,
            "sizing_authority": "journal=nat2",
            "manual_spacing_overrides": [],
            "figure_inches": [figure_width, figure_height],
            "axes_geometry": axes_geometry,
            "minimum_horizontal_decorated_gap_inches": min(horizontal_decorated_gaps),
            "minimum_vertical_decorated_gap_inches": min(vertical_decorated_gaps),
            "all_axes_decorated_bboxes_inside_canvas": all_axes_contained,
            "adjacent_decorated_bboxes_do_not_overlap": decorated_nonoverlap,
            "text_outside_canvas": text_outside_canvas,
        },
        "style_scope": {
            "rc_changed_before": rc_changed_before,
            "rc_changed_after_render": rc_changed_after_render,
            "rc_context_did_not_leak": rc_context_did_not_leak,
            "explicit_overrides": [
                "Colorblind-safe categorical row colors from UltraPlot's colorblind cycle.",
                "Small translucent rasterized markers to reveal dense raw-pair distributions.",
                "Gray dashed 1:1 reference and black solid OLS fit for line-type distinction.",
                "Small annotation text with a translucent white backing for legibility over points.",
                "Gridlines disabled because the shared axes and 1:1 reference carry the comparison.",
            ],
            "figure_or_subplot_titles_present": False,
        },
        "exports": {
            "export_dpi_for_every_save_call": EXPORT_DPI,
            "export_dpi_greater_than_600": EXPORT_DPI > 600,
            "pdf_path": report_relative_path(PDF_PATH, VERIFICATION_PATH),
            "pdf_bytes": PDF_PATH.stat().st_size,
            "pdf_media_box_points": [pdf_width_points, pdf_height_points],
            "pdf_size_mm": [pdf_width_mm, pdf_height_mm],
            "pdf_width_matches_nat2_within_0.2_mm": pdf_width_matches_nat2,
            "pdf_canvas_matches_figure": pdf_canvas_matches_figure,
            "pdf_required_text_present": pdf_required_text_present,
            "pdf_embedded_raster_layer_count": len(pdf_raster_layers),
            "pdf_embedded_raster_layers": pdf_raster_layers,
            "pdf_embedded_raster_effective_dpi_range": [
                min(pdf_raster_dpi_values),
                max(pdf_raster_dpi_values),
            ],
            "pdf_embedded_raster_dpi_matches_export_dpi": pdf_raster_dpi_matches,
            "png_path": report_relative_path(PNG_PATH, VERIFICATION_PATH),
            "png_bytes": PNG_PATH.stat().st_size,
            "png_pixels": png_pixels,
            "expected_png_pixels_at_export_dpi": expected_png_pixels,
            "png_dimensions_match": png_dimensions_match,
            "png_dpi_metadata": png_dpi_metadata,
            "png_dpi_metadata_matches": png_dpi_matches,
        },
    }
    VERIFICATION_PATH.write_text(
        json.dumps(verification, indent=2), encoding="ascii"
    )
    print(json.dumps(verification["exports"], indent=2))
    print(
        "Minimum decorated gaps (horizontal, vertical): "
        f"{min(horizontal_decorated_gaps):.4f} in, "
        f"{min(vertical_decorated_gaps):.4f} in"
    )
    print(f"Verification passed: {passed}")
    print(f"Wrote {VERIFICATION_PATH}")

    if not passed:
        raise RuntimeError(
            "Render verification failed; inspect verification_with_skill.json."
        )


if __name__ == "__main__":
    main()
