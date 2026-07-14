#!/usr/bin/env python
"""Render-time geometry and encoding QA for Matplotlib/UltraPlot figures.

Use :func:`audit_figure` after every artist, legend, and colorbar has been added and
before saving. The function forces a final draw, measures geometry in display space,
and returns a JSON-serializable report. It complements, but does not replace,
file-level checks in ``check_figure.py`` or scientific review of the figure.
"""

from __future__ import annotations

import argparse
import itertools
import math
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
from matplotlib.collections import PathCollection
from matplotlib.legend import Legend
from matplotlib.lines import Line2D
from matplotlib.transforms import Bbox


def _json_number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _bbox_values(bbox: Bbox | None) -> list[float] | None:
    if bbox is None:
        return None
    values = [float(bbox.x0), float(bbox.y0), float(bbox.x1), float(bbox.y1)]
    if not all(math.isfinite(value) for value in values):
        return None
    return values


def _valid_bbox(bbox: Bbox | None) -> bool:
    values = _bbox_values(bbox)
    return bool(values and values[2] >= values[0] and values[3] >= values[1])


def _union_bboxes(bboxes: Sequence[Bbox]) -> Bbox | None:
    valid = [bbox for bbox in bboxes if _valid_bbox(bbox)]
    return Bbox.union(valid) if valid else None


def _path_collection_bbox(artist: PathCollection, dpi: float) -> Bbox | None:
    """Approximate a PathCollection bbox from offsets and marker areas.

    ``PathCollection.get_window_extent`` often returns an infinite bbox for legend
    handles. Marker sizes are areas in points squared, so a conservative circular
    envelope is sufficient for collision and containment checks.
    """
    try:
        offsets = np.asarray(artist.get_offsets(), dtype=float)
        if offsets.ndim == 1:
            offsets = offsets.reshape(1, -1)
        if offsets.size == 0 or offsets.shape[1] < 2:
            return None
        centers = np.asarray(artist.get_offset_transform().transform(offsets[:, :2]))
        sizes = np.asarray(artist.get_sizes(), dtype=float).reshape(-1)
        if sizes.size == 0:
            sizes = np.array([0.0])
        if sizes.size == 1 and centers.shape[0] > 1:
            sizes = np.repeat(sizes, centers.shape[0])
        elif sizes.size != centers.shape[0]:
            sizes = np.resize(sizes, centers.shape[0])
        linewidths = np.asarray(artist.get_linewidths(), dtype=float).reshape(-1)
        linewidth = float(np.nanmax(linewidths)) if linewidths.size else 0.0
        radii_px = (np.sqrt(np.clip(sizes, 0, None)) + linewidth) * dpi / 144.0
        boxes = [
            Bbox.from_extents(x - radius, y - radius, x + radius, y + radius)
            for (x, y), radius in zip(centers, radii_px, strict=False)
            if math.isfinite(x) and math.isfinite(y) and math.isfinite(radius)
        ]
        return _union_bboxes(boxes)
    except Exception:  # noqa: BLE001 - caller records unavailable geometry.
        return None


def _artist_bbox(artist: Any, renderer: Any, dpi: float) -> Bbox | None:
    if isinstance(artist, PathCollection):
        bbox = _path_collection_bbox(artist, dpi)
        if _valid_bbox(bbox):
            return bbox
    for method_name in ("get_window_extent", "get_tightbbox"):
        method = getattr(artist, method_name, None)
        if method is None:
            continue
        try:
            bbox = method(renderer)
        except TypeError:
            try:
                bbox = method()
            except Exception:  # noqa: BLE001
                continue
        except Exception:  # noqa: BLE001
            continue
        if _valid_bbox(bbox):
            return bbox
    return None


def _overlap_and_gap(a: Bbox, b: Bbox) -> tuple[float, float, float]:
    overlap_x = min(a.x1, b.x1) - max(a.x0, b.x0)
    overlap_y = min(a.y1, b.y1) - max(a.y0, b.y0)
    gap_x = max(a.x0 - b.x1, b.x0 - a.x1, 0.0)
    gap_y = max(a.y0 - b.y1, b.y0 - a.y1, 0.0)
    return overlap_x, overlap_y, math.hypot(gap_x, gap_y)


def _containment_overflow(outer: Bbox, inner: Bbox) -> tuple[float, float, float, float]:
    return (
        max(outer.x0 - inner.x0, 0.0),
        max(inner.x1 - outer.x1, 0.0),
        max(outer.y0 - inner.y0, 0.0),
        max(inner.y1 - outer.y1, 0.0),
    )


def _add_issue(
    report: dict[str, Any],
    severity: str,
    code: str,
    message: str,
    **context: Any,
) -> None:
    payload = {"code": code, "message": message}
    if context:
        payload["context"] = context
    report["errors" if severity == "error" else "warnings"].append(payload)


def _legend_label(legend: Legend, index: int) -> str:
    title = legend.get_title().get_text().strip() if legend.get_title() else ""
    return title or f"legend_{index + 1}"


def _audit_pair(
    report: dict[str, Any],
    legend_report: dict[str, Any],
    *,
    kind: str,
    first_name: str,
    first_bbox: Bbox | None,
    second_name: str,
    second_bbox: Bbox | None,
    pixels_per_point: float,
    min_gap_pt: float,
    overlap_tolerance_pt: float,
) -> None:
    if not _valid_bbox(first_bbox) or not _valid_bbox(second_bbox):
        return
    overlap_x, overlap_y, gap_px = _overlap_and_gap(first_bbox, second_bbox)
    tolerance_px = overlap_tolerance_pt * pixels_per_point
    if overlap_x > tolerance_px and overlap_y > tolerance_px:
        item = {
            "kind": kind,
            "first": first_name,
            "second": second_name,
            "overlap_width_pt": overlap_x / pixels_per_point,
            "overlap_height_pt": overlap_y / pixels_per_point,
        }
        legend_report["collisions"].append(item)
        _add_issue(
            report,
            "error",
            "legend_internal_overlap",
            f"{legend_report['name']}: {kind} overlap between {first_name} and {second_name}",
            **item,
        )
    elif gap_px < min_gap_pt * pixels_per_point:
        gap_pt = gap_px / pixels_per_point
        item = {
            "kind": kind,
            "first": first_name,
            "second": second_name,
            "gap_pt": gap_pt,
        }
        legend_report["small_gaps"].append(item)
        _add_issue(
            report,
            "warning",
            "legend_small_gap",
            f"{legend_report['name']}: {kind} gap is below {min_gap_pt:g} pt",
            **item,
        )


def _audit_legends(
    fig: Any,
    renderer: Any,
    report: dict[str, Any],
    *,
    min_gap_pt: float,
    overlap_tolerance_pt: float,
    containment_tolerance_pt: float,
) -> None:
    dpi = float(fig.dpi)
    pixels_per_point = dpi / 72.0
    tolerance_px = containment_tolerance_pt * pixels_per_point
    figure_bbox = fig.bbox
    legends = [legend for legend in fig.findobj(match=Legend) if legend.get_visible()]
    report["legend_count"] = len(legends)

    for index, legend in enumerate(legends):
        legend_bbox = _artist_bbox(legend, renderer, dpi)
        title = legend.get_title()
        title_bbox = None
        title_text = ""
        if title is not None and title.get_visible():
            title_text = title.get_text().strip()
            if title_text:
                title_bbox = _artist_bbox(title, renderer, dpi)

        handles = list(getattr(legend, "legend_handles", ()) or ())
        texts = [text for text in legend.get_texts() if text.get_visible() and text.get_text().strip()]
        handle_boxes = [_artist_bbox(handle, renderer, dpi) for handle in handles]
        text_boxes = [_artist_bbox(text, renderer, dpi) for text in texts]
        ncols = int(getattr(legend, "_ncols", 1) or 1)
        legend_report: dict[str, Any] = {
            "name": _legend_label(legend, index),
            "index": index,
            "ncols": ncols,
            "bbox_px": _bbox_values(legend_bbox),
            "entry_count": max(len(handles), len(texts)),
            "collisions": [],
            "small_gaps": [],
            "containment": [],
        }

        for handle_index, text_index in itertools.product(range(len(handles)), range(len(texts))):
            relation = "same_entry" if handle_index == text_index else "cross_entry"
            _audit_pair(
                report,
                legend_report,
                kind=f"handle_text_{relation}",
                first_name=f"handle[{handle_index}]",
                first_bbox=handle_boxes[handle_index],
                second_name=f"text[{text_index}]={texts[text_index].get_text()!r}",
                second_bbox=text_boxes[text_index],
                pixels_per_point=pixels_per_point,
                min_gap_pt=min_gap_pt,
                overlap_tolerance_pt=overlap_tolerance_pt,
            )

        for first, second in itertools.combinations(range(len(handles)), 2):
            _audit_pair(
                report,
                legend_report,
                kind="handle_handle",
                first_name=f"handle[{first}]",
                first_bbox=handle_boxes[first],
                second_name=f"handle[{second}]",
                second_bbox=handle_boxes[second],
                pixels_per_point=pixels_per_point,
                min_gap_pt=min_gap_pt,
                overlap_tolerance_pt=overlap_tolerance_pt,
            )

        for first, second in itertools.combinations(range(len(texts)), 2):
            _audit_pair(
                report,
                legend_report,
                kind="text_text",
                first_name=f"text[{first}]={texts[first].get_text()!r}",
                first_bbox=text_boxes[first],
                second_name=f"text[{second}]={texts[second].get_text()!r}",
                second_bbox=text_boxes[second],
                pixels_per_point=pixels_per_point,
                min_gap_pt=min_gap_pt,
                overlap_tolerance_pt=overlap_tolerance_pt,
            )

        if title_bbox is not None:
            for entry_type, boxes in (("handle", handle_boxes), ("text", text_boxes)):
                for entry_index, entry_bbox in enumerate(boxes):
                    _audit_pair(
                        report,
                        legend_report,
                        kind="title_entry",
                        first_name=f"title={title_text!r}",
                        first_bbox=title_bbox,
                        second_name=f"{entry_type}[{entry_index}]",
                        second_bbox=entry_bbox,
                        pixels_per_point=pixels_per_point,
                        min_gap_pt=min_gap_pt,
                        overlap_tolerance_pt=overlap_tolerance_pt,
                    )

        if _valid_bbox(legend_bbox):
            overflow = _containment_overflow(figure_bbox, legend_bbox)
            if max(overflow) > tolerance_px:
                overflow_pt = [value / pixels_per_point for value in overflow]
                _add_issue(
                    report,
                    "error",
                    "legend_outside_figure",
                    f"{legend_report['name']} extends outside the final figure canvas",
                    overflow_left_right_bottom_top_pt=overflow_pt,
                )

            contained_artists = [
                (f"handle[{i}]", bbox) for i, bbox in enumerate(handle_boxes)
            ] + [(f"text[{i}]", bbox) for i, bbox in enumerate(text_boxes)]
            if title_bbox is not None:
                contained_artists.append(("title", title_bbox))
            for artist_name, artist_bbox in contained_artists:
                if not _valid_bbox(artist_bbox):
                    _add_issue(
                        report,
                        "warning",
                        "legend_geometry_unavailable",
                        f"{legend_report['name']}: could not measure {artist_name}",
                    )
                    continue
                artist_overflow = _containment_overflow(legend_bbox, artist_bbox)
                if max(artist_overflow) > tolerance_px:
                    overflow_pt = [value / pixels_per_point for value in artist_overflow]
                    containment = {
                        "artist": artist_name,
                        "overflow_left_right_bottom_top_pt": overflow_pt,
                    }
                    legend_report["containment"].append(containment)
                    _add_issue(
                        report,
                        "error",
                        "legend_artist_outside_frame",
                        f"{legend_report['name']}: {artist_name} extends outside the legend box",
                        **containment,
                    )
        else:
            _add_issue(
                report,
                "warning",
                "legend_geometry_unavailable",
                f"Could not measure {legend_report['name']}",
            )

        report["legends"].append(legend_report)


def _same_numeric_values(first: Any, second: Any) -> bool:
    try:
        a = np.asarray(first, dtype=float).reshape(-1)
        b = np.asarray(second, dtype=float).reshape(-1)
    except (TypeError, ValueError):
        return False
    return a.shape == b.shape and np.allclose(a, b, equal_nan=True, rtol=1e-9, atol=1e-12)


def _numeric_summary(values: Any) -> dict[str, Any]:
    """Return a compact JSON-safe summary without serializing every value."""
    array = np.asarray(values, dtype=float).reshape(-1)
    finite = array[np.isfinite(array)]
    summary: dict[str, Any] = {
        "count": int(array.size),
        "finite_count": int(finite.size),
        "nonfinite_count": int(array.size - finite.size),
    }
    if finite.size:
        summary.update(
            {
                "min": float(np.min(finite)),
                "max": float(np.max(finite)),
                "unique_count": int(np.unique(finite).size),
            }
        )
    else:
        summary.update({"min": None, "max": None, "unique_count": 0})
    return summary


def _comparison_summary(
    actual: Any,
    expected: Any,
    *,
    rtol: float,
    atol: float,
    max_examples: int = 5,
) -> dict[str, Any]:
    """Summarize a numeric comparison and retain only a few mismatches."""
    actual_array = np.asarray(actual, dtype=float).reshape(-1)
    expected_array = np.asarray(expected, dtype=float).reshape(-1)
    summary: dict[str, Any] = {
        "actual_count": int(actual_array.size),
        "expected_count": int(expected_array.size),
        "mismatch_count": 0,
        "max_absolute_error": None,
        "max_relative_error": None,
        "first_mismatches": [],
    }
    if actual_array.shape != expected_array.shape:
        summary["shape_match"] = False
        summary["mismatch_count"] = int(max(actual_array.size, expected_array.size))
        return summary

    summary["shape_match"] = True
    if not actual_array.size:
        return summary

    finite = np.isfinite(actual_array) & np.isfinite(expected_array)
    absolute_error = np.full(actual_array.shape, np.inf, dtype=float)
    absolute_error[finite] = np.abs(actual_array[finite] - expected_array[finite])
    tolerance = atol + rtol * np.abs(expected_array)
    matches = finite & (absolute_error <= tolerance)
    mismatch_indices = np.flatnonzero(~matches)
    summary["mismatch_count"] = int(mismatch_indices.size)

    finite_errors = absolute_error[np.isfinite(absolute_error)]
    if finite_errors.size:
        summary["max_absolute_error"] = float(np.max(finite_errors))
        denominator = np.maximum(np.abs(expected_array[finite]), atol)
        relative_error = absolute_error[finite] / denominator
        summary["max_relative_error"] = float(np.max(relative_error))

    examples = []
    for index in mismatch_indices[:max_examples]:
        examples.append(
            {
                "index": int(index),
                "actual": _json_number(actual_array[index]),
                "expected": _json_number(expected_array[index]),
                "absolute_error": _json_number(absolute_error[index]),
            }
        )
    summary["first_mismatches"] = examples
    return summary


def _scale_ultraplot_size_values(
    values: Any,
    source: Any,
    *,
    smin: float | None,
    smax: float | None,
    area_size: bool | None,
    absolute_size: bool | None,
) -> np.ndarray:
    import matplotlib as mpl

    scaled = np.asarray(values, dtype=float)
    source_array = np.asarray(source, dtype=float)
    area = True if area_size is None else bool(area_size)
    absolute = source_array.size == 1 if absolute_size is None else bool(absolute_size)
    if not absolute or smin is not None or smax is not None:
        lower_size = 1.0 if smin is None else float(smin)
        default_max = float(mpl.rcParams["lines.markersize"]) ** (2 if area else 1)
        upper_size = default_max if smax is None else float(smax)
        finite = source_array[np.isfinite(source_array)]
        if finite.size:
            data_min = float(np.nanmin(finite))
            data_max = float(np.nanmax(finite))
            if data_min != data_max:
                scaled = lower_size + (upper_size - lower_size) * (
                    scaled - data_min
                ) / (data_max - data_min)
    return scaled if area else np.square(scaled)


def _legend_marker_areas(legend: Legend) -> np.ndarray:
    areas: list[float] = []
    for handle in list(getattr(legend, "legend_handles", ()) or ()):
        if isinstance(handle, Line2D):
            areas.append(float(handle.get_markersize()) ** 2)
        elif isinstance(handle, PathCollection):
            sizes = np.asarray(handle.get_sizes(), dtype=float).reshape(-1)
            areas.append(float(sizes[0]) if sizes.size else math.nan)
        elif hasattr(handle, "get_markersize"):
            areas.append(float(handle.get_markersize()) ** 2)
        else:
            areas.append(math.nan)
    return np.asarray(areas, dtype=float)


def _audit_size_encodings(
    report: dict[str, Any],
    size_encodings: Sequence[Mapping[str, Any]],
    *,
    include_raw_arrays: bool,
) -> None:
    for index, spec in enumerate(size_encodings):
        name = str(spec.get("name") or f"size_encoding_{index + 1}")
        item_report: dict[str, Any] = {"name": name}
        scatter = spec.get("scatter")
        legend = spec.get("legend")
        levels = spec.get("levels")
        semantic_values = spec.get("values")
        expected_areas = spec.get("expected_areas")
        rtol = float(spec.get("rtol", 1e-6))
        atol = float(spec.get("atol_pt2", 1e-6))

        if scatter is None or legend is None or levels is None:
            _add_issue(
                report,
                "error",
                "size_encoding_spec_incomplete",
                f"{name}: provide scatter, legend, and levels",
            )
            report["size_encodings"].append(item_report)
            continue

        metadata = getattr(scatter, "_ultraplot_size_scale", None)
        scatter_areas = np.asarray(scatter.get_sizes(), dtype=float).reshape(-1)
        legend_areas = _legend_marker_areas(legend)
        item_report["scatter_area_summary_pt2"] = _numeric_summary(scatter_areas)
        item_report["legend_areas_pt2"] = legend_areas.tolist()
        if include_raw_arrays:
            item_report["scatter_areas_pt2"] = scatter_areas.tolist()

        if expected_areas is not None:
            expected_level_areas = np.asarray(expected_areas, dtype=float).reshape(-1)
        elif metadata:
            source = metadata.get("values")
            if semantic_values is None:
                semantic_values = source
            elif not _same_numeric_values(semantic_values, source):
                _add_issue(
                    report,
                    "error",
                    "scatter_semantic_values_mismatch",
                    f"{name}: scatter size input differs from the declared semantic values; possible pre-scaling or double scaling",
                )
            expected_level_areas = _scale_ultraplot_size_values(
                levels,
                semantic_values,
                smin=metadata.get("smin"),
                smax=metadata.get("smax"),
                area_size=metadata.get("area_size"),
                absolute_size=metadata.get("absolute_size"),
            )
            expected_scatter_areas = _scale_ultraplot_size_values(
                semantic_values,
                semantic_values,
                smin=metadata.get("smin"),
                smax=metadata.get("smax"),
                area_size=metadata.get("area_size"),
                absolute_size=metadata.get("absolute_size"),
            ).reshape(-1)
            item_report["expected_scatter_area_summary_pt2"] = _numeric_summary(
                expected_scatter_areas
            )
            if include_raw_arrays:
                item_report["expected_scatter_areas_pt2"] = expected_scatter_areas.tolist()
            compared_expected = (
                expected_scatter_areas
                if scatter_areas.size != 1
                else expected_scatter_areas[:1]
            )
            scatter_comparison = _comparison_summary(
                scatter_areas,
                compared_expected,
                rtol=rtol,
                atol=atol,
            )
            item_report["scatter_mapping"] = scatter_comparison
            if (
                scatter_areas.size not in {1, expected_scatter_areas.size}
                or scatter_comparison["mismatch_count"]
            ):
                _add_issue(
                    report,
                    "error",
                    "scatter_size_mapping_mismatch",
                    f"{name}: rendered scatter areas do not match the declared UltraPlot size mapping",
                    comparison=scatter_comparison,
                )
        else:
            _add_issue(
                report,
                "warning",
                "scatter_size_metadata_missing",
                f"{name}: scatter has no UltraPlot size-scale metadata; pass expected_areas for an explicit audit",
            )
            expected_level_areas = np.asarray([], dtype=float)

        item_report["expected_legend_areas_pt2"] = expected_level_areas.tolist()
        if expected_level_areas.size:
            legend_comparison = _comparison_summary(
                legend_areas,
                expected_level_areas,
                rtol=rtol,
                atol=atol,
            )
            item_report["legend_mapping"] = legend_comparison
            if legend_areas.size != expected_level_areas.size:
                _add_issue(
                    report,
                    "error",
                    "sizelegend_entry_count_mismatch",
                    f"{name}: legend has {legend_areas.size} handles for {expected_level_areas.size} levels",
                    comparison=legend_comparison,
                )
            elif legend_comparison["mismatch_count"]:
                _add_issue(
                    report,
                    "error",
                    "sizelegend_mapping_mismatch",
                    f"{name}: size-legend marker areas do not match the scatter mapping",
                    comparison=legend_comparison,
                )
        report["size_encodings"].append(item_report)


def _norm_signature(norm: Any) -> dict[str, Any]:
    signature: dict[str, Any] = {
        "class": f"{type(norm).__module__}.{type(norm).__name__}",
        "vmin": _json_number(getattr(norm, "vmin", None)),
        "vmax": _json_number(getattr(norm, "vmax", None)),
        "clip": bool(getattr(norm, "clip", False)),
    }
    for attr in ("vcenter", "linthresh", "linscale", "gamma", "base"):
        if hasattr(norm, attr):
            signature[attr] = _json_number(getattr(norm, attr))
    boundaries = getattr(norm, "boundaries", None)
    if boundaries is not None:
        try:
            signature["boundaries"] = np.asarray(boundaries, dtype=float).tolist()
        except (TypeError, ValueError):
            signature["boundaries"] = str(boundaries)
    return signature


def _norms_equivalent(first: dict[str, Any], second: dict[str, Any]) -> bool:
    if first.keys() != second.keys():
        return False
    for key in first:
        a, b = first[key], second[key]
        if isinstance(a, list) or isinstance(b, list):
            try:
                if not np.allclose(np.asarray(a, dtype=float), np.asarray(b, dtype=float)):
                    return False
            except (TypeError, ValueError):
                if a != b:
                    return False
        elif isinstance(a, float) or isinstance(b, float):
            if a is None or b is None:
                if a != b:
                    return False
            elif not math.isclose(float(a), float(b), rel_tol=1e-9, abs_tol=1e-12):
                return False
        elif a != b:
            return False
    return True


def _audit_shared_color_encodings(
    report: dict[str, Any], shared_color_encodings: Sequence[Mapping[str, Any]]
) -> None:
    for index, spec in enumerate(shared_color_encodings):
        name = str(spec.get("name") or f"shared_color_{index + 1}")
        mappables = list(spec.get("mappables") or ())
        colorbars = list(spec.get("colorbars") or ())
        if spec.get("colorbar") is not None:
            colorbars.append(spec["colorbar"])
        expected_ticks = spec.get("expected_ticks")
        item_report: dict[str, Any] = {"name": name, "norms": [], "ticks": []}

        if len(mappables) < 2:
            _add_issue(
                report,
                "warning",
                "shared_color_spec_small",
                f"{name}: fewer than two mappables were supplied for a shared-scale audit",
            )

        signatures = [_norm_signature(mappable.norm) for mappable in mappables]
        item_report["norms"] = signatures
        if signatures and any(
            not _norms_equivalent(signatures[0], signature)
            for signature in signatures[1:]
        ):
            _add_issue(
                report,
                "error",
                "shared_color_norm_mismatch",
                f"{name}: shared-color mappables use different normalization",
            )

        for colorbar in colorbars:
            ticks = np.asarray(colorbar.get_ticks(), dtype=float)
            item_report["ticks"].append(ticks.tolist())
            if signatures:
                colorbar_signature = _norm_signature(colorbar.mappable.norm)
                if not _norms_equivalent(signatures[0], colorbar_signature):
                    _add_issue(
                        report,
                        "error",
                        "colorbar_norm_mismatch",
                        f"{name}: colorbar normalization differs from its mappables",
                    )
            if expected_ticks is not None and not np.allclose(
                ticks,
                np.asarray(expected_ticks, dtype=float),
                rtol=float(spec.get("rtol", 1e-8)),
                atol=float(spec.get("atol", 1e-10)),
            ):
                _add_issue(
                    report,
                    "error",
                    "colorbar_ticks_mismatch",
                    f"{name}: colorbar ticks differ from expected data-unit ticks",
                )

        if len(item_report["ticks"]) > 1:
            first_ticks = np.asarray(item_report["ticks"][0], dtype=float)
            for ticks in item_report["ticks"][1:]:
                other = np.asarray(ticks, dtype=float)
                if first_ticks.shape != other.shape or not np.allclose(first_ticks, other):
                    _add_issue(
                        report,
                        "error",
                        "shared_colorbar_ticks_mismatch",
                        f"{name}: colorbars for a shared encoding use different ticks",
                    )
                    break
        report["shared_color_encodings"].append(item_report)


def _audit_continuous_color_encodings(
    report: dict[str, Any],
    continuous_color_encodings: Sequence[Mapping[str, Any]],
) -> None:
    default_quantiles = np.asarray([0.05, 0.25, 0.5, 0.75, 0.95], dtype=float)
    for index, spec in enumerate(continuous_color_encodings):
        name = str(spec.get("name") or f"continuous_color_{index + 1}")
        values = spec.get("values")
        mappable = spec.get("mappable")
        norm = spec.get("norm") or getattr(mappable, "norm", None)
        item_report: dict[str, Any] = {"name": name}

        try:
            array = np.asarray(values, dtype=float).reshape(-1)
        except (TypeError, ValueError):
            _add_issue(
                report,
                "error",
                "continuous_color_values_invalid",
                f"{name}: values must be a numeric array",
            )
            report["continuous_color_encodings"].append(item_report)
            continue
        array = array[np.isfinite(array)]
        if not array.size:
            _add_issue(
                report,
                "error",
                "continuous_color_values_empty",
                f"{name}: values contain no finite observations",
            )
            report["continuous_color_encodings"].append(item_report)
            continue
        if not callable(norm):
            _add_issue(
                report,
                "error",
                "continuous_color_norm_missing",
                f"{name}: provide the live normalization or mappable",
            )
            report["continuous_color_encodings"].append(item_report)
            continue

        quantiles = np.asarray(spec.get("quantiles", default_quantiles), dtype=float)
        if (
            quantiles.ndim != 1
            or quantiles.size < 3
            or np.any(~np.isfinite(quantiles))
            or np.any((quantiles < 0) | (quantiles > 1))
            or np.any(np.diff(quantiles) <= 0)
        ):
            _add_issue(
                report,
                "error",
                "continuous_color_quantiles_invalid",
                f"{name}: quantiles must be increasing finite values in [0, 1]",
            )
            report["continuous_color_encodings"].append(item_report)
            continue

        data_quantiles = np.quantile(array, quantiles)
        try:
            normalized_quantiles = np.ma.asarray(norm(data_quantiles), dtype=float).filled(
                np.nan
            )
        except (TypeError, ValueError) as exc:
            _add_issue(
                report,
                "error",
                "continuous_color_norm_failed",
                f"{name}: normalization failed for data quantiles: {exc}",
            )
            report["continuous_color_encodings"].append(item_report)
            continue

        item_report.update(
            {
                "count": int(array.size),
                "data_range": [float(array.min()), float(array.max())],
                "quantiles": quantiles.tolist(),
                "data_quantiles": data_quantiles.tolist(),
                "normalized_quantiles": normalized_quantiles.tolist(),
                "norm": _norm_signature(norm),
            }
        )
        if quantiles.size >= 5:
            middle_50_span = float(normalized_quantiles[-2] - normalized_quantiles[1])
            middle_90_span = float(normalized_quantiles[-1] - normalized_quantiles[0])
            item_report["middle_50_normalized_span"] = middle_50_span
            item_report["middle_90_normalized_span"] = middle_90_span
            for key, observed in (
                ("min_middle_50_span", middle_50_span),
                ("min_middle_90_span", middle_90_span),
            ):
                threshold = spec.get(key)
                if threshold is not None and observed < float(threshold):
                    _add_issue(
                        report,
                        "warning",
                        "continuous_color_scale_compression",
                        f"{name}: {key.removeprefix('min_')} is {observed:.3f}, "
                        f"below the configured diagnostic threshold {float(threshold):.3f}",
                        name=name,
                        metric=key.removeprefix("min_"),
                        observed=observed,
                        threshold=float(threshold),
                    )
        report["continuous_color_encodings"].append(item_report)


def _parse_expected_size(expected_size_mm: Any) -> tuple[float | None, float | None]:
    if expected_size_mm is None:
        return None, None
    if isinstance(expected_size_mm, Mapping):
        width = expected_size_mm.get("width", expected_size_mm.get("width_mm"))
        height = expected_size_mm.get("height", expected_size_mm.get("height_mm"))
        return _json_number(width), _json_number(height)
    if isinstance(expected_size_mm, Sequence) and not isinstance(expected_size_mm, (str, bytes)):
        values = list(expected_size_mm)
        if len(values) != 2:
            raise ValueError("expected_size_mm must contain width and height")
        return _json_number(values[0]), _json_number(values[1])
    raise TypeError("expected_size_mm must be a mapping or a two-item sequence")


def audit_figure(
    fig: Any,
    expected_size_mm: Any = None,
    size_encodings: Sequence[Mapping[str, Any]] = (),
    shared_color_encodings: Sequence[Mapping[str, Any]] = (),
    continuous_color_encodings: Sequence[Mapping[str, Any]] = (),
    min_gap_pt: float = 1.0,
    overlap_tolerance_pt: float = 0.25,
    containment_tolerance_pt: float = 0.5,
    physical_size_tolerance_mm: float = 0.5,
    include_raw_arrays: bool = False,
) -> dict[str, Any]:
    """Audit final figure geometry and selected semantic encodings.

    Parameters
    ----------
    fig
        Matplotlib or UltraPlot figure. Add every artist and guide before calling.
    expected_size_mm
        Optional ``(width_mm, height_mm)`` pair or mapping. Use ``None`` for an
        unconstrained dimension in mapping form.
    size_encodings
        Sequence of mappings with ``scatter``, ``legend``, ``levels``, and usually
        ``values``. ``values`` must be the semantic data supplied to ``scatter(s=)``.
        For an explicit precomputed-area workflow, supply ``expected_areas``.
    shared_color_encodings
        Sequence of mappings with ``mappables`` and optional ``colorbar`` or
        ``colorbars`` and ``expected_ticks``.
    continuous_color_encodings
        Sequence of mappings with semantic ``values`` and a live ``norm`` or
        ``mappable``. Reports data and normalized quantiles. Optional
        ``min_middle_50_span`` and ``min_middle_90_span`` values enable explicitly
        configured compression warnings; they are diagnostics, not journal rules.
    min_gap_pt, overlap_tolerance_pt, containment_tolerance_pt
        Skill QA policy thresholds measured in physical points. These are not
        universal journal rules.
    physical_size_tolerance_mm
        Allowed difference from ``expected_size_mm`` after the final draw.
    include_raw_arrays
        Include every scatter and expected marker area in the returned report. Keep
        this disabled for normal QA; compact summaries and mismatch examples are
        returned by default.
    """
    if min_gap_pt < 0 or overlap_tolerance_pt < 0 or containment_tolerance_pt < 0:
        raise ValueError("geometry tolerances must be non-negative")

    before_in = np.asarray(fig.get_size_inches(), dtype=float)
    fig.canvas.draw()
    after_in = np.asarray(fig.get_size_inches(), dtype=float)
    if not np.allclose(before_in, after_in, rtol=0, atol=1e-10):
        # UltraPlot journal/auto-layout sizing can update on draw. Draw once more so
        # every artist extent comes from the final canvas.
        fig.canvas.draw()
        after_in = np.asarray(fig.get_size_inches(), dtype=float)
    renderer = fig.canvas.get_renderer()

    report: dict[str, Any] = {
        "figure_size_before_draw_in": before_in.tolist(),
        "figure_size_after_draw_in": after_in.tolist(),
        "figure_size_after_draw_mm": (after_in * 25.4).tolist(),
        "size_changed_on_draw": bool(not np.allclose(before_in, after_in, rtol=0, atol=1e-10)),
        "thresholds": {
            "min_gap_pt": float(min_gap_pt),
            "overlap_tolerance_pt": float(overlap_tolerance_pt),
            "containment_tolerance_pt": float(containment_tolerance_pt),
            "physical_size_tolerance_mm": float(physical_size_tolerance_mm),
        },
        "legends": [],
        "size_encodings": [],
        "shared_color_encodings": [],
        "continuous_color_encodings": [],
        "warnings": [],
        "errors": [],
    }

    expected_width, expected_height = _parse_expected_size(expected_size_mm)
    report["expected_size_mm"] = [expected_width, expected_height]
    observed_mm = after_in * 25.4
    for axis_name, observed, expected in zip(
        ("width", "height"), observed_mm, (expected_width, expected_height), strict=True
    ):
        if expected is not None and abs(float(observed) - expected) > physical_size_tolerance_mm:
            _add_issue(
                report,
                "error",
                "physical_size_mismatch",
                f"Final figure {axis_name} is {observed:.3f} mm; expected {expected:.3f} mm",
                axis=axis_name,
                observed_mm=float(observed),
                expected_mm=expected,
            )

    _audit_legends(
        fig,
        renderer,
        report,
        min_gap_pt=min_gap_pt,
        overlap_tolerance_pt=overlap_tolerance_pt,
        containment_tolerance_pt=containment_tolerance_pt,
    )
    _audit_size_encodings(
        report,
        size_encodings,
        include_raw_arrays=include_raw_arrays,
    )
    _audit_shared_color_encodings(report, shared_color_encodings)
    _audit_continuous_color_encodings(report, continuous_color_encodings)

    report["summary"] = {
        "warning_count": len(report["warnings"]),
        "error_count": len(report["errors"]),
        "ok": not report["errors"],
    }
    report["ok"] = report["summary"]["ok"]
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    print(
        "Import audit_figure(fig, ...) from this module and call it after all artists "
        "and guides have been added. Use check_figure.py after saving."
    )


if __name__ == "__main__":
    main()
