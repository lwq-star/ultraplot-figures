#!/usr/bin/env python
"""Stable public QA facade for UltraPlot publication figures.

Use :func:`audit_draft_figure` before production export and
:func:`audit_submission_figure` after saving the requested deliverables. The facade
keeps render, semantic, artifact, and output-lifecycle checks behind one documented
interface while delivered plotting scripts remain independent of this skill.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import tempfile
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any

try:
    from check_figure import KNOWN_EXTS, audit_files
    from render_qa import audit_figure
    from semantic_qa import audit_figure_contract, audit_task_contract
except ModuleNotFoundError:  # Support namespace-style ``scripts.figure_qa`` imports.
    from .check_figure import KNOWN_EXTS, audit_files
    from .render_qa import audit_figure
    from .semantic_qa import audit_figure_contract, audit_task_contract


class FigureQAError(RuntimeError):
    """Raised when a stable QA report contains a hard defect."""


def _resolved(path: str | Path) -> Path:
    return Path(path).expanduser().resolve(strict=False)


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


@contextmanager
def qa_workspace(
    *,
    root: str | Path | None = None,
    prefix: str = "ultraplot-qa-",
    keep: bool = False,
) -> Iterator[Path]:
    """Create QA-only storage outside the delivery directory by default."""
    parent = _resolved(root) if root is not None else None
    if parent is not None:
        parent.mkdir(parents=True, exist_ok=True)
    if keep:
        yield Path(tempfile.mkdtemp(prefix=prefix, dir=parent))
        return
    with tempfile.TemporaryDirectory(prefix=prefix, dir=parent) as directory:
        yield Path(directory)


def audit_output_separation(
    deliverables: Mapping[str, str | Path],
    qa_artifacts: Sequence[str | Path] = (),
    *,
    delivery_dir: str | Path | None = None,
    qa_root: str | Path | None = None,
) -> dict[str, Any]:
    """Verify that persistent deliverables and temporary QA files do not overlap."""
    errors: list[str] = []
    normalized_deliverables: dict[str, str] = {}
    deliverable_paths: set[Path] = set()
    for role, raw_path in deliverables.items():
        if not isinstance(role, str) or not role.strip():
            errors.append("deliverable roles must be non-empty strings")
            continue
        path = _resolved(raw_path)
        if path in deliverable_paths:
            errors.append(f"duplicate deliverable path: {path}")
        deliverable_paths.add(path)
        normalized_deliverables[role.strip()] = str(path)

    normalized_qa = [_resolved(path) for path in qa_artifacts]
    delivery_root = _resolved(delivery_dir) if delivery_dir is not None else None
    temporary_root = _resolved(qa_root) if qa_root is not None else None
    for path in normalized_qa:
        if path in deliverable_paths:
            errors.append(f"path is both a deliverable and a QA artifact: {path}")
        if delivery_root is not None and _is_within(path, delivery_root):
            errors.append(f"QA artifact is inside the delivery directory: {path}")
        if temporary_root is not None and not _is_within(path, temporary_root):
            errors.append(f"QA artifact is outside the declared QA root: {path}")

    return {
        "deliverables": normalized_deliverables,
        "qa_artifacts": [str(path) for path in normalized_qa],
        "delivery_dir": str(delivery_root) if delivery_root is not None else None,
        "qa_root": str(temporary_root) if temporary_root is not None else None,
        "errors": errors,
        "ok": not errors,
    }


def publication_fallback_policy(
    *,
    expected_width_mm: float,
    expected_height_mm: float | None = None,
    additional_formats: Sequence[str] = (),
) -> dict[str, Any]:
    """Return the fully unspecified-target PDF plus RGB/LZW TIFF artifact policy."""
    if expected_width_mm is None:
        raise ValueError("expected_width_mm is required for the fallback policy")
    width = float(expected_width_mm)
    if not math.isfinite(width) or width <= 0:
        raise ValueError("expected_width_mm must be a finite positive number")
    height = None if expected_height_mm is None else float(expected_height_mm)
    if height is not None and (not math.isfinite(height) or height <= 0):
        raise ValueError("expected_height_mm must be a finite positive number")

    allowed_formats = {"pdf", "tiff", *additional_formats}
    return {
        "allow_formats": allowed_formats,
        "require_formats": {"pdf", "tiff"},
        "min_effective_dpi": 600.0,
        "expected_width_mm": width,
        "expected_height_mm": height,
        "size_tolerance_mm": 0.5,
        "require_embedded_fonts": True,
        "forbid_type3_fonts": True,
        "forbid_alpha": True,
        "require_tiff_mode": "RGB",
        "require_tiff_compression": "LZW",
        "strict": True,
        "fail_on_warning": True,
    }


def save_draft_preview(
    fig: Any,
    path: str | Path,
    *,
    dpi: float = 180.0,
) -> Path:
    """Save a temporary low-DPI PNG without changing production output policy."""
    if not 0 < dpi <= 300:
        raise ValueError("draft preview dpi must be greater than 0 and at most 300")
    output = _resolved(path)
    if output.suffix.lower() != ".png":
        raise ValueError("draft previews must use a .png path")
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(
        output,
        format="png",
        dpi=dpi,
        facecolor="white",
        transparent=False,
    )
    return output


def _combine_reports(
    *,
    stage: str,
    render: dict[str, Any],
    semantic: dict[str, Any],
    separation: dict[str, Any],
    artifact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    gates = {
        "render": bool(render.get("ok")),
        "semantic": bool(semantic.get("ok")),
        "output_separation": bool(separation.get("ok")),
    }
    if artifact is not None:
        gates["artifact"] = bool(artifact.get("summary", {}).get("ok"))

    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    for gate, report in (
        ("render", render),
        ("semantic", semantic),
        ("output_separation", separation),
        ("artifact", artifact),
    ):
        if report is None:
            continue
        gate_errors = report.get("errors", [])
        gate_warnings = report.get("warnings", [])
        if gate_errors:
            errors.append({"gate": gate, "items": gate_errors})
        if gate_warnings:
            warnings.append({"gate": gate, "items": gate_warnings})
        if gate == "artifact":
            figure_warnings = [
                {"path": item.get("path"), "items": item.get("warnings", [])}
                for item in report.get("figures", [])
                if item.get("warnings")
            ]
            figure_errors = [
                {"path": item.get("path"), "items": item.get("errors", [])}
                for item in report.get("figures", [])
                if item.get("errors")
            ]
            if figure_errors:
                errors.append({"gate": gate, "items": figure_errors})
            if figure_warnings:
                warnings.append({"gate": gate, "items": figure_warnings})

    result: dict[str, Any] = {
        "stage": stage,
        "gates": gates,
        "deliverables": separation["deliverables"],
        "qa_artifacts": separation["qa_artifacts"],
        "render": render,
        "semantic": semantic,
        "output_separation": separation,
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "gate_count": len(gates),
            "passed_gate_count": sum(gates.values()),
            "error_group_count": len(errors),
            "warning_group_count": len(warnings),
            "ok": all(gates.values()),
        },
    }
    if artifact is not None:
        result["artifact"] = artifact
    result["ok"] = result["summary"]["ok"]
    return result


def _audit_live_figure(
    fig: Any,
    *,
    stage: str,
    expected: dict[str, Any],
    axes_registry: dict[str, Any],
    encoding_evidence: dict[str, dict[str, Any]],
    request_text: str,
    target_filter: dict[str, Any] | None,
    counts: dict[str, Any] | None,
    deliverables: Mapping[str, str | Path],
    qa_artifacts: Sequence[str | Path],
    delivery_dir: str | Path | None,
    qa_root: str | Path | None,
    expected_size_mm: Any,
    size_encodings: Sequence[Mapping[str, Any]],
    shared_color_encodings: Sequence[Mapping[str, Any]],
    continuous_color_encodings: Sequence[Mapping[str, Any]],
    allow_subplot_titles: bool,
    layout_override_reasons: Mapping[str, str] | None,
    require_output_files: bool,
    include_raw_arrays: bool,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    separation = audit_output_separation(
        deliverables,
        qa_artifacts,
        delivery_dir=delivery_dir,
        qa_root=qa_root,
    )
    output_paths = [Path(path) for path in separation["deliverables"].values()]
    render = audit_figure(
        fig,
        expected_size_mm=expected_size_mm,
        size_encodings=size_encodings,
        shared_color_encodings=shared_color_encodings,
        continuous_color_encodings=continuous_color_encodings,
        include_raw_arrays=include_raw_arrays,
    )
    semantic = audit_figure_contract(
        fig,
        expected,
        axes_registry,
        encoding_evidence,
        request_text=request_text,
        target_filter=target_filter,
        counts=counts,
        output_paths=output_paths,
        allow_subplot_titles=allow_subplot_titles,
        layout_override_reasons=layout_override_reasons,
        require_output_files=require_output_files,
    )
    return render, semantic, separation


def audit_draft_figure(
    fig: Any,
    *,
    expected: dict[str, Any],
    axes_registry: dict[str, Any],
    encoding_evidence: dict[str, dict[str, Any]],
    request_text: str,
    target_filter: dict[str, Any] | None,
    counts: dict[str, Any] | None,
    deliverables: Mapping[str, str | Path],
    qa_artifacts: Sequence[str | Path] = (),
    delivery_dir: str | Path | None = None,
    qa_root: str | Path | None = None,
    expected_size_mm: Any = None,
    size_encodings: Sequence[Mapping[str, Any]] = (),
    shared_color_encodings: Sequence[Mapping[str, Any]] = (),
    continuous_color_encodings: Sequence[Mapping[str, Any]] = (),
    allow_subplot_titles: bool = False,
    layout_override_reasons: Mapping[str, str] | None = None,
    include_raw_arrays: bool = False,
) -> dict[str, Any]:
    """Run live semantic and render QA before production files are written."""
    render, semantic, separation = _audit_live_figure(
        fig,
        stage="draft",
        expected=expected,
        axes_registry=axes_registry,
        encoding_evidence=encoding_evidence,
        request_text=request_text,
        target_filter=target_filter,
        counts=counts,
        deliverables=deliverables,
        qa_artifacts=qa_artifacts,
        delivery_dir=delivery_dir,
        qa_root=qa_root,
        expected_size_mm=expected_size_mm,
        size_encodings=size_encodings,
        shared_color_encodings=shared_color_encodings,
        continuous_color_encodings=continuous_color_encodings,
        allow_subplot_titles=allow_subplot_titles,
        layout_override_reasons=layout_override_reasons,
        require_output_files=False,
        include_raw_arrays=include_raw_arrays,
    )
    return _combine_reports(
        stage="draft",
        render=render,
        semantic=semantic,
        separation=separation,
    )


def audit_submission_figure(
    fig: Any,
    *,
    expected: dict[str, Any],
    axes_registry: dict[str, Any],
    encoding_evidence: dict[str, dict[str, Any]],
    request_text: str,
    target_filter: dict[str, Any] | None,
    counts: dict[str, Any] | None,
    deliverables: Mapping[str, str | Path],
    artifact_policy: Mapping[str, Any],
    qa_artifacts: Sequence[str | Path] = (),
    delivery_dir: str | Path | None = None,
    qa_root: str | Path | None = None,
    expected_size_mm: Any = None,
    size_encodings: Sequence[Mapping[str, Any]] = (),
    shared_color_encodings: Sequence[Mapping[str, Any]] = (),
    continuous_color_encodings: Sequence[Mapping[str, Any]] = (),
    allow_subplot_titles: bool = False,
    layout_override_reasons: Mapping[str, str] | None = None,
    include_raw_arrays: bool = False,
) -> dict[str, Any]:
    """Run final live QA plus saved-artifact QA for submission deliverables."""
    render, semantic, separation = _audit_live_figure(
        fig,
        stage="final",
        expected=expected,
        axes_registry=axes_registry,
        encoding_evidence=encoding_evidence,
        request_text=request_text,
        target_filter=target_filter,
        counts=counts,
        deliverables=deliverables,
        qa_artifacts=qa_artifacts,
        delivery_dir=delivery_dir,
        qa_root=qa_root,
        expected_size_mm=expected_size_mm,
        size_encodings=size_encodings,
        shared_color_encodings=shared_color_encodings,
        continuous_color_encodings=continuous_color_encodings,
        allow_subplot_titles=allow_subplot_titles,
        layout_override_reasons=layout_override_reasons,
        require_output_files=True,
        include_raw_arrays=include_raw_arrays,
    )
    figure_paths = [
        Path(path)
        for path in separation["deliverables"].values()
        if Path(path).suffix.lower() in KNOWN_EXTS
    ]
    if figure_paths:
        artifact = audit_files(figure_paths, **dict(artifact_policy))
    else:
        artifact = {
            "errors": ["no saved figure deliverables were supplied"],
            "summary": {
                "figure_count": 0,
                "warning_count": 0,
                "error_count": 1,
                "ok": False,
            },
            "figures": [],
        }
    return _combine_reports(
        stage="final",
        render=render,
        semantic=semantic,
        separation=separation,
        artifact=artifact,
    )


def compact_summary(report: Mapping[str, Any]) -> dict[str, Any]:
    """Return the small result intended for normal terminal output."""
    render = report.get("render", {})
    artifact = report.get("artifact", {})
    stage = report.get("stage")
    ok = bool(report.get("ok"))
    if not ok:
        status = "hard_defects"
        next_action = "fix hard defects, redraw, and rerun the failed stage"
    elif stage == "draft":
        status = "draft_qa_passed"
        next_action = "inspect one draft preview, then save production outputs"
    else:
        status = "final_qa_passed"
        next_action = "perform one final-scale visual inspection, then deliver"
    return {
        "stage": stage,
        "ok": ok,
        "status": status,
        "next_action": next_action,
        "gates": report.get("gates", {}),
        "figure_size_after_draw_mm": render.get("figure_size_after_draw_mm"),
        "artifact_summary": artifact.get("summary") if artifact else None,
        "deliverables": report.get("deliverables", {}),
        "error_group_count": len(report.get("errors", [])),
        "warning_group_count": len(report.get("warnings", [])),
        "warnings_are_nonblocking": ok,
    }


def require_ok(report: Mapping[str, Any]) -> None:
    """Raise a compact exception when any hard QA gate fails."""
    if report.get("ok"):
        return
    summary = compact_summary(report)
    raise FigureQAError(json.dumps(summary, ensure_ascii=False, separators=(",", ":")))


EXAMPLE = """\
from io import BytesIO

import ultraplot as uplt
from PIL import Image

from figure_qa import (
    audit_draft_figure,
    audit_submission_figure,
    publication_fallback_policy,
    qa_workspace,
    require_ok,
    save_draft_preview,
)


def save_final_outputs(fig):
    with uplt.rc.context({"pdf.fonttype": 42, "ps.fonttype": 42}):
        fig.savefig(pdf_path, format="pdf", facecolor="white", transparent=False)
    with BytesIO() as buffer:
        fig.savefig(
            buffer,
            format="png",
            dpi=600,
            facecolor="white",
            transparent=False,
        )
        buffer.seek(0)
        with Image.open(buffer) as image:
            with image.convert("RGB") as rgb_image:
                rgb_image.save(
                    tif_path,
                    format="TIFF",
                    dpi=(600, 600),
                    compression="tiff_lzw",
                )


# EXPECTED_CONTRACT is defined once from the original request.
with qa_workspace() as qa_dir:
    draft_preview = qa_dir / "draft-preview.png"
    draft = audit_draft_figure(
        fig,
        expected=EXPECTED_CONTRACT,
        axes_registry=axes_registry,
        encoding_evidence=encoding_evidence,
        request_text=REQUEST_TEXT,
        target_filter=ACTUAL_FILTER,
        counts=filter_counts,
        deliverables={"python": script_path, "pdf": pdf_path, "tiff": tif_path},
        qa_artifacts=[draft_preview],
        delivery_dir=script_path.parent,
        qa_root=qa_dir,
        expected_size_mm={"width": TARGET_WIDTH_MM, "height": None},
        size_encodings=size_encoding_specs,
    )
    require_ok(draft)
    save_draft_preview(fig, draft_preview, dpi=180)

    # Inspect a temporary 150-200 dpi preview, then save final outputs once.
    save_final_outputs(fig)
    final = audit_submission_figure(
        fig,
        expected=EXPECTED_CONTRACT,
        axes_registry=axes_registry,
        encoding_evidence=encoding_evidence,
        request_text=REQUEST_TEXT,
        target_filter=ACTUAL_FILTER,
        counts=filter_counts,
        deliverables={"python": script_path, "pdf": pdf_path, "tiff": tif_path},
        artifact_policy=publication_fallback_policy(
            expected_width_mm=TARGET_WIDTH_MM
        ),
        delivery_dir=script_path.parent,
        qa_root=qa_dir,
        expected_size_mm={"width": TARGET_WIDTH_MM, "height": None},
        size_encodings=size_encoding_specs,
    )
    require_ok(final)
"""


def _self_test() -> dict[str, Any]:
    from io import BytesIO

    gdal_data = Path(sys.prefix) / "Library" / "share" / "gdal"
    if "GDAL_DATA" not in os.environ and gdal_data.exists():
        os.environ["GDAL_DATA"] = str(gdal_data)

    import matplotlib

    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt
    import numpy as np
    import ultraplot as uplt
    from matplotlib import colors as mcolors
    from PIL import Image

    values = np.array([5.0, 6.0, 7.0])
    x = np.arange(values.size, dtype=float)
    y = np.array([1.0, 2.0, 1.5])
    request_text = (
        "Create one scientific scatter plot that compares values using marker area, "
        "and provide a Python script, PDF, and TIFF."
    )
    expected_contract = {
        "contract_version": 2,
        "figure_purpose": "Show how marker area represents the value field.",
        "reader_judgment": "Compare values across the three points.",
        "requested_judgments": [
            {
                "id": "value_comparison",
                "request_span": "compares values",
                "question": "How do values differ across the points?",
                "evidence_kind": "comparison",
                "fields": ["value"],
            }
        ],
        "target_filter": None,
        "panels": ["main"],
        "encodings": {
            "main.x": "x",
            "main.y": "y",
            "main.size": "value",
        },
        "evidence_map": {
            "value_comparison": [
                {
                    "panel": "main",
                    "channels": ["main.size"],
                    "justification": (
                        "The request explicitly asks for marker area in one scatter plot."
                    ),
                }
            ]
        },
        "outputs": ["python", "pdf", "tiff"],
        "target_policy": {
            "formats": {
                "value": ["python", "pdf", "tiff"],
                "source": "user",
            },
            "width_mm": {"value": 183.0, "source": "size_fallback:nat2"},
            "height_mm": {"value": None, "source": "automatic"},
            "tiff_dpi": {"value": 600, "source": "raster_fallback"},
        },
    }
    with qa_workspace() as run_root:
        delivery_dir = run_root / "delivery"
        temporary_dir = run_root / "qa"
        delivery_dir.mkdir()
        temporary_dir.mkdir()
        script_path = delivery_dir / "plot.py"
        pdf_path = delivery_dir / "figure.pdf"
        tif_path = delivery_dir / "figure.tif"
        script_path.write_text(
            "import ultraplot as uplt\nfig, ax = uplt.subplots()\n",
            encoding="utf-8",
        )

        target_width_mm = 183.0
        fig, axs = uplt.subplots(journal="nat2", refheight=1.8)
        ax = axs[0]
        points = ax.scatter(x, y, s=values, smin=8, smax=80)
        handles, labels = ax.sizelegend(
            values,
            values=values,
            smin=8,
            smax=80,
            add=False,
        )
        legend = ax.legend(
            handles,
            labels,
            title="Value",
            loc="r",
            ncols=1,
            frame=False,
            borderpad="4pt",
            handletextpad="7pt",
            labelspacing="8pt",
            columnspacing="8pt",
        )
        report = audit_draft_figure(
            fig,
            expected=expected_contract,
            axes_registry={"main": ax},
            encoding_evidence={
                "main.x": {"field": "x", "artist": points, "values": x, "kind": "x"},
                "main.y": {"field": "y", "artist": points, "values": y, "kind": "y"},
                "main.size": {
                    "field": "value",
                    "artist": points,
                    "values": values,
                    "kind": "size",
                },
            },
            request_text=request_text,
            target_filter=None,
            counts=None,
            deliverables={
                "python": script_path,
                "pdf": pdf_path,
                "tiff": tif_path,
            },
            qa_artifacts=[temporary_dir / "draft-preview.png"],
            delivery_dir=delivery_dir,
            qa_root=temporary_dir,
            expected_size_mm={"width": target_width_mm, "height": None},
            size_encodings=[
                {
                    "name": "value",
                    "scatter": points,
                    "legend": legend,
                    "levels": values,
                    "values": values,
                }
            ],
            continuous_color_encodings=[
                {
                    "name": "value_diagnostic",
                    "values": values,
                    "norm": mcolors.Normalize(vmin=values.min(), vmax=values.max()),
                }
            ],
        )
        require_ok(report)
        preview_path = save_draft_preview(
            fig,
            temporary_dir / "draft-preview.png",
            dpi=180,
        )
        if not preview_path.is_file():
            raise AssertionError("draft preview was not created")
        size_report = report["render"]["size_encodings"][0]
        if "scatter_areas_pt2" in size_report:
            raise AssertionError("raw scatter arrays must be disabled by default")
        color_report = report["render"]["continuous_color_encodings"][0]
        if "normalized_quantiles" not in color_report:
            raise AssertionError("continuous-color quantile diagnostics are missing")

        chinese_request = (
            "请绘制变量A的分布，并提供Python脚本、PDF和高分辨率TIFF，不需要PNG。"
        )
        chinese_expected = {
            "contract_version": 2,
            "figure_purpose": "Show the distribution of variable A.",
            "reader_judgment": "Judge the range and concentration of variable A.",
            "requested_judgments": [
                {
                    "id": "variable_distribution",
                    "request_span": "变量A的分布",
                    "question": "How is variable A distributed?",
                    "evidence_kind": "distribution",
                    "fields": ["value"],
                }
            ],
            "target_filter": None,
            "panels": ["distribution"],
            "encodings": {
                "distribution.x": "value",
                "distribution.height": "count",
            },
            "evidence_map": {
                "variable_distribution": [
                    {
                        "panel": "distribution",
                        "channels": ["distribution.x", "distribution.height"],
                    }
                ]
            },
            "outputs": ["python", "pdf", "tiff"],
            "target_policy": {
                "formats": {
                    "value": ["python", "pdf", "tiff"],
                    "source": "user",
                },
                "width_mm": {"value": 183.0, "source": "size_fallback:nat2"},
                "height_mm": {"value": None, "source": "automatic"},
                "tiff_dpi": {"value": 600, "source": "raster_fallback"},
            },
        }
        chinese_actual = {
            "target_filter": None,
            "panels": ["distribution"],
            "encodings": {
                "distribution.x": "value",
                "distribution.height": "count",
            },
            "outputs": ["python", "pdf", "tiff"],
        }
        chinese_report = audit_task_contract(
            {
                "request_text": chinese_request,
                "expected": chinese_expected,
                "actual": chinese_actual,
            }
        )
        if not chinese_report["ok"]:
            raise AssertionError(chinese_report["errors"])
        if chinese_report["request_checks"]["requested_outputs"] != [
            "python",
            "pdf",
            "tiff",
        ]:
            raise AssertionError("Chinese output-role or negation parsing failed")

        with uplt.rc.context({"pdf.fonttype": 42, "ps.fonttype": 42}):
            fig.savefig(pdf_path, format="pdf", facecolor="white", transparent=False)
        with BytesIO() as buffer:
            fig.savefig(
                buffer,
                format="png",
                dpi=600,
                facecolor="white",
                transparent=False,
            )
            buffer.seek(0)
            with Image.open(buffer) as image:
                with image.convert("RGB") as rgb_image:
                    rgb_image.save(
                        tif_path,
                        format="TIFF",
                        dpi=(600, 600),
                        compression="tiff_lzw",
                    )

        final_report = audit_submission_figure(
            fig,
            expected=expected_contract,
            axes_registry={"main": ax},
            encoding_evidence={
                "main.x": {"field": "x", "artist": points, "values": x, "kind": "x"},
                "main.y": {"field": "y", "artist": points, "values": y, "kind": "y"},
                "main.size": {
                    "field": "value",
                    "artist": points,
                    "values": values,
                    "kind": "size",
                },
            },
            request_text=request_text,
            target_filter=None,
            counts=None,
            deliverables={
                "python": script_path,
                "pdf": pdf_path,
                "tiff": tif_path,
            },
            artifact_policy=publication_fallback_policy(
                expected_width_mm=target_width_mm
            ),
            delivery_dir=delivery_dir,
            qa_root=temporary_dir,
            expected_size_mm={"width": target_width_mm, "height": None},
            size_encodings=[
                {
                    "name": "value",
                    "scatter": points,
                    "legend": legend,
                    "levels": values,
                    "values": values,
                }
            ],
            continuous_color_encodings=[
                {
                    "name": "value_diagnostic",
                    "values": values,
                    "norm": mcolors.Normalize(vmin=values.min(), vmax=values.max()),
                }
            ],
        )
        require_ok(final_report)
        plt.close(fig)
        return compact_summary(final_report)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--example", action="store_true", help="Print the stable API example")
    parser.add_argument("--self-test", action="store_true", help="Run a temporary smoke test")
    args = parser.parse_args()
    if args.example:
        print(EXAMPLE)
        return 0
    if args.self_test:
        print(json.dumps(_self_test(), ensure_ascii=False, indent=2))
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
