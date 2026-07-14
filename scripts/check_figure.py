#!/usr/bin/env python
"""Inspect exported scientific-figure files after saving.

This is artifact-level QA. It checks formats, physical dimensions, raster resolution,
PDF resources, and selected delivery policies. It cannot determine whether the
scientific message, labels, legend semantics, colors, or statistics are correct; run
``render_qa.audit_figure`` before saving and inspect the rendered figure visually.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

RASTER_EXTS = {".png", ".tif", ".tiff", ".jpg", ".jpeg"}
VECTOR_EXTS = {".pdf", ".svg", ".eps"}
KNOWN_EXTS = RASTER_EXTS | VECTOR_EXTS
CANONICAL_EXT = {".tiff": ".tif", ".jpeg": ".jpg"}
DPI_ABS_TOLERANCE = 0.01
DPI_REL_TOLERANCE = 1e-6
TIFF_COMPRESSION_ALIASES = {
    "1": "none",
    "5": "lzw",
    "8": "deflate",
    "32773": "packbits",
    "32946": "deflate",
    "none": "none",
    "raw": "none",
    "uncompressed": "none",
    "lzw": "lzw",
    "tiff_lzw": "lzw",
    "adobe_deflate": "deflate",
    "deflate": "deflate",
    "tiff_adobe_deflate": "deflate",
    "tiff_deflate": "deflate",
    "packbits": "packbits",
    "tiff_packbits": "packbits",
}


def canonical_ext(value: str) -> str:
    value = value.strip().lower()
    if not value:
        return value
    if not value.startswith("."):
        value = f".{value}"
    return CANONICAL_EXT.get(value, value)


def normalize_tiff_mode(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip().upper()
    return normalized or None


def normalize_tiff_compression(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    if not normalized:
        return None
    return TIFF_COMPRESSION_ALIASES.get(normalized, normalized.removeprefix("tiff_"))


def parse_formats(value: str | None) -> set[str] | None:
    if not value:
        return None
    formats = {canonical_ext(item) for item in value.split(",") if item.strip()}
    return formats or None


def add_issue(
    result: dict[str, Any],
    message: str,
    *,
    error: bool = False,
    strict: bool = False,
) -> None:
    result["errors" if error or strict else "warnings"].append(message)


def finite_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def physical_size_mm(width_in: float, height_in: float) -> list[float]:
    return [float(width_in) * 25.4, float(height_in) * 25.4]


def dpi_is_below(observed: float, required: float) -> bool:
    """Ignore normal raster-metadata and PDF placement rounding at the threshold."""
    tolerance = max(DPI_ABS_TOLERANCE, abs(required) * DPI_REL_TOLERANCE)
    return observed < required - tolerance


def check_expected_size(
    result: dict[str, Any],
    observed_mm: list[float] | tuple[float, float] | None,
    *,
    expected_width_mm: float | None,
    expected_height_mm: float | None,
    tolerance_mm: float,
    source: str,
) -> None:
    if expected_width_mm is None and expected_height_mm is None:
        return
    if observed_mm is None:
        add_issue(result, f"cannot verify expected physical size from {source}", error=True)
        return
    for name, observed, expected in zip(
        ("width", "height"), observed_mm, (expected_width_mm, expected_height_mm), strict=True
    ):
        if expected is None:
            continue
        if abs(float(observed) - float(expected)) > tolerance_mm:
            add_issue(
                result,
                f"{source} {name} is {observed:.3f} mm; expected {expected:.3f} mm "
                f"within {tolerance_mm:g} mm",
                error=True,
            )


def inspect_raster(
    path: Path,
    result: dict[str, Any],
    *,
    min_effective_dpi: float,
    min_width_px: int | None,
    min_height_px: int | None,
    expected_width_mm: float | None,
    expected_height_mm: float | None,
    size_tolerance_mm: float,
    forbid_alpha: bool,
    require_tiff_mode: str | None,
    require_tiff_compression: str | None,
    strict: bool,
) -> None:
    try:
        from PIL import Image

        with Image.open(path) as image:
            image.load()
            width, height = image.size
            result["format"] = image.format
            result["pixels"] = [int(width), int(height)]
            result["mode"] = image.mode
            result["bands"] = list(image.getbands())

            dpi_info = image.info.get("dpi")
            observed_mm: list[float] | None = None
            if dpi_info:
                dpi_x = finite_float(dpi_info[0])
                dpi_y = finite_float(dpi_info[1] if len(dpi_info) > 1 else dpi_info[0])
                if dpi_x and dpi_y and dpi_x > 0 and dpi_y > 0:
                    result["effective_dpi"] = [dpi_x, dpi_y]
                    observed_mm = physical_size_mm(width / dpi_x, height / dpi_y)
                    result["physical_size_mm"] = observed_mm
                    if dpi_is_below(min(dpi_x, dpi_y), min_effective_dpi):
                        add_issue(
                            result,
                            f"raster effective DPI is below {min_effective_dpi:g}: "
                            f"{min(dpi_x, dpi_y):.3f}",
                            strict=strict,
                        )
                else:
                    add_issue(result, "raster DPI metadata is invalid", strict=strict)
            else:
                add_issue(result, "raster DPI metadata is missing", strict=strict)

            check_expected_size(
                result,
                observed_mm,
                expected_width_mm=expected_width_mm,
                expected_height_mm=expected_height_mm,
                tolerance_mm=size_tolerance_mm,
                source="raster metadata",
            )
            if min_width_px is not None and width < min_width_px:
                add_issue(result, f"raster width is below {min_width_px}px: {width}px", strict=strict)
            if min_height_px is not None and height < min_height_px:
                add_issue(result, f"raster height is below {min_height_px}px: {height}px", strict=strict)

            has_alpha = "A" in image.getbands() or "transparency" in image.info
            result["has_alpha"] = bool(has_alpha)
            if forbid_alpha and has_alpha:
                add_issue(result, "raster contains an alpha/transparency channel", error=True)

            if canonical_ext(path.suffix) == ".tif":
                actual_mode = normalize_tiff_mode(image.mode)
                if require_tiff_mode is not None and actual_mode != require_tiff_mode:
                    add_issue(
                        result,
                        f"TIFF mode is {actual_mode or 'unknown'}; required {require_tiff_mode}",
                        error=True,
                    )

                compression = image.info.get("compression")
                if compression is None:
                    try:
                        compression = image.tag_v2.get(259)
                    except Exception:  # noqa: BLE001 - metadata is optional.
                        compression = None
                result["tiff_compression"] = str(compression) if compression is not None else None
                normalized_compression = normalize_tiff_compression(compression)
                result["tiff_compression_normalized"] = normalized_compression
                if (
                    require_tiff_compression is not None
                    and normalized_compression != require_tiff_compression
                ):
                    add_issue(
                        result,
                        "TIFF compression is "
                        f"{normalized_compression or 'unknown'}; required "
                        f"{require_tiff_compression}",
                        error=True,
                    )
                elif normalized_compression in {None, "none"}:
                    add_issue(
                        result,
                        "TIFF appears uncompressed; verify the target journal's file-size policy",
                    )

            if canonical_ext(path.suffix) == ".jpg":
                add_issue(result, "JPEG is lossy and is not recommended for scientific plots")
    except Exception as exc:  # noqa: BLE001 - preserve a machine-readable report.
        add_issue(result, f"could not read raster image: {exc}", error=True)

def resolve_pdf_object(value: Any) -> Any:
    try:
        return value.get_object()
    except Exception:  # noqa: BLE001
        return value


def pdf_box_points(box: Any) -> list[float]:
    return [float(box.width), float(box.height)]


def pdf_box_mm(box: Any) -> list[float]:
    points = pdf_box_points(box)
    return [points[0] * 25.4 / 72.0, points[1] * 25.4 / 72.0]


def font_descriptor(font: Any) -> Any | None:
    descriptor = font.get("/FontDescriptor") if hasattr(font, "get") else None
    return resolve_pdf_object(descriptor) if descriptor is not None else None


def descriptor_embedded(descriptor: Any | None) -> bool:
    if descriptor is None or not hasattr(descriptor, "get"):
        return False
    return any(descriptor.get(key) is not None for key in ("/FontFile", "/FontFile2", "/FontFile3"))


def inspect_pdf_fonts(page: Any) -> list[dict[str, Any]]:
    resources = resolve_pdf_object(page.get("/Resources")) or {}
    font_map = resolve_pdf_object(resources.get("/Font")) if hasattr(resources, "get") else None
    if not font_map:
        return []

    fonts: list[dict[str, Any]] = []
    for resource_name, font_ref in font_map.items():
        font = resolve_pdf_object(font_ref)
        subtype = str(font.get("/Subtype", ""))
        base_font = str(font.get("/BaseFont", resource_name))
        type3 = subtype == "/Type3"
        embedded = type3
        descendant_subtypes: list[str] = []
        if subtype == "/Type0":
            descendants = resolve_pdf_object(font.get("/DescendantFonts")) or []
            embedded_flags: list[bool] = []
            for descendant_ref in descendants:
                descendant = resolve_pdf_object(descendant_ref)
                descendant_subtypes.append(str(descendant.get("/Subtype", "")))
                embedded_flags.append(descriptor_embedded(font_descriptor(descendant)))
            embedded = bool(embedded_flags) and all(embedded_flags)
        elif not type3:
            embedded = descriptor_embedded(font_descriptor(font))
        fonts.append(
            {
                "resource": str(resource_name),
                "base_font": base_font,
                "subtype": subtype,
                "descendant_subtypes": descendant_subtypes,
                "embedded": bool(embedded),
                "type3": bool(type3),
            }
        )
    return fonts


def inspect_pdf_transparency(page: Any) -> list[dict[str, Any]]:
    resources = resolve_pdf_object(page.get("/Resources")) or {}
    findings: list[dict[str, Any]] = []
    ext_gstate = resolve_pdf_object(resources.get("/ExtGState")) if hasattr(resources, "get") else None
    if ext_gstate:
        for name, state_ref in ext_gstate.items():
            state = resolve_pdf_object(state_ref)
            fill_alpha = finite_float(state.get("/ca", 1.0))
            stroke_alpha = finite_float(state.get("/CA", 1.0))
            smask = str(state.get("/SMask", "/None"))
            blend_mode = str(state.get("/BM", "/Normal"))
            transparent = (
                (fill_alpha is not None and fill_alpha < 0.999999)
                or (stroke_alpha is not None and stroke_alpha < 0.999999)
                or smask not in {"/None", "None"}
                or blend_mode not in {"/Normal", "Normal"}
            )
            if transparent:
                findings.append(
                    {
                        "resource": str(name),
                        "fill_alpha": fill_alpha,
                        "stroke_alpha": stroke_alpha,
                        "soft_mask": smask,
                        "blend_mode": blend_mode,
                    }
                )

    xobjects = resolve_pdf_object(resources.get("/XObject")) if hasattr(resources, "get") else None
    if xobjects:
        for name, xref in xobjects.items():
            xobj = resolve_pdf_object(xref)
            if str(xobj.get("/Subtype", "")) == "/Image" and (
                xobj.get("/SMask") is not None or xobj.get("/Mask") is not None
            ):
                findings.append({"resource": str(name), "image_mask": True})
    return findings


def multiply_pdf_matrix(left: list[float], right: list[float]) -> list[float]:
    """Return the affine product ``left @ right`` in PDF six-number form."""
    a1, b1, c1, d1, e1, f1 = left
    a2, b2, c2, d2, e2, f2 = right
    return [
        a1 * a2 + c1 * b2,
        b1 * a2 + d1 * b2,
        a1 * c2 + c1 * d2,
        b1 * c2 + d1 * d2,
        a1 * e2 + c1 * f2 + e1,
        b1 * e2 + d1 * f2 + f1,
    ]


def inspect_pdf_images(page: Any, reader: Any) -> tuple[list[dict[str, Any]], list[str]]:
    resources = resolve_pdf_object(page.get("/Resources")) or {}
    xobjects = resolve_pdf_object(resources.get("/XObject")) if hasattr(resources, "get") else None
    if not xobjects:
        return [], []

    image_objects: dict[str, dict[str, Any]] = {}
    for name, xref in xobjects.items():
        xobj = resolve_pdf_object(xref)
        if str(xobj.get("/Subtype", "")) == "/Image":
            image_objects[str(name)] = {
                "resource": str(name),
                "pixels": [int(xobj.get("/Width", 0)), int(xobj.get("/Height", 0))],
                "uses": [],
            }
    if not image_objects:
        return [], []

    warnings: list[str] = []
    try:
        from pypdf.generic import ContentStream

        contents = page.get_contents()
        if contents is None:
            return list(image_objects.values()), ["page has image resources but no content stream"]
        stream = ContentStream(contents, reader)
        current = [1.0, 0.0, 0.0, 1.0, 0.0, 0.0]
        stack: list[list[float]] = []
        for operands, operator in stream.operations:
            if operator == b"q":
                stack.append(current.copy())
            elif operator == b"Q":
                current = stack.pop() if stack else [1.0, 0.0, 0.0, 1.0, 0.0, 0.0]
            elif operator == b"cm" and len(operands) >= 6:
                matrix = [float(value) for value in operands[:6]]
                current = multiply_pdf_matrix(current, matrix)
            elif operator == b"Do" and operands:
                name = str(operands[0])
                if name not in image_objects:
                    continue
                width_pt = math.hypot(current[0], current[1])
                height_pt = math.hypot(current[2], current[3])
                width_px, height_px = image_objects[name]["pixels"]
                dpi_x = width_px * 72.0 / width_pt if width_pt > 0 else None
                dpi_y = height_px * 72.0 / height_pt if height_pt > 0 else None
                image_objects[name]["uses"].append(
                    {
                        "display_size_points": [width_pt, height_pt],
                        "effective_dpi": [dpi_x, dpi_y],
                    }
                )
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"could not parse PDF image placement operators: {exc}")

    for image in image_objects.values():
        if not image["uses"]:
            warnings.append(f"could not measure displayed size for PDF image {image['resource']}")
    return list(image_objects.values()), warnings

def inspect_pdf(
    path: Path,
    result: dict[str, Any],
    *,
    min_effective_dpi: float,
    expected_width_mm: float | None,
    expected_height_mm: float | None,
    size_tolerance_mm: float,
    require_embedded_fonts: bool,
    forbid_type3_fonts: bool,
    forbid_transparency: bool,
    strict: bool,
) -> None:
    try:
        with path.open("rb") as handle:
            header = handle.read(5)
        if header != b"%PDF-":
            add_issue(result, "PDF header is missing or invalid", strict=strict)
    except OSError as exc:
        add_issue(result, f"could not read PDF header: {exc}", error=True)
        return

    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        result["pdf_pages"] = len(reader.pages)
        if not reader.pages:
            add_issue(result, "PDF has zero pages", error=True)
            return

        page_sizes: list[dict[str, Any]] = []
        fonts_by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
        transparency: list[dict[str, Any]] = []
        images: list[dict[str, Any]] = []
        for page_index, page in enumerate(reader.pages):
            media_mm = pdf_box_mm(page.mediabox)
            crop_mm = pdf_box_mm(page.cropbox)
            page_sizes.append(
                {
                    "page": page_index + 1,
                    "mediabox_points": pdf_box_points(page.mediabox),
                    "mediabox_mm": media_mm,
                    "cropbox_points": pdf_box_points(page.cropbox),
                    "cropbox_mm": crop_mm,
                }
            )
            for font in inspect_pdf_fonts(page):
                key = (font["resource"], font["base_font"], font["subtype"])
                fonts_by_key[key] = font
            for finding in inspect_pdf_transparency(page):
                transparency.append({"page": page_index + 1, **finding})
            page_images, image_warnings = inspect_pdf_images(page, reader)
            for image in page_images:
                images.append({"page": page_index + 1, **image})
            for warning in image_warnings:
                add_issue(result, f"page {page_index + 1}: {warning}")

        result["pdf_page_boxes"] = page_sizes
        result["pdf_mediabox_mm"] = page_sizes[0]["mediabox_mm"]
        result["pdf_cropbox_mm"] = page_sizes[0]["cropbox_mm"]
        check_expected_size(
            result,
            page_sizes[0]["cropbox_mm"],
            expected_width_mm=expected_width_mm,
            expected_height_mm=expected_height_mm,
            tolerance_mm=size_tolerance_mm,
            source="PDF CropBox",
        )
        first_crop = page_sizes[0]["cropbox_mm"]
        if any(
            max(abs(a - b) for a, b in zip(first_crop, item["cropbox_mm"], strict=True))
            > size_tolerance_mm
            for item in page_sizes[1:]
        ):
            add_issue(result, "PDF pages do not share the same CropBox size", strict=strict)

        fonts = list(fonts_by_key.values())
        result["pdf_fonts"] = fonts
        result["pdf_font_count"] = len(fonts)
        unembedded = [font for font in fonts if not font["embedded"]]
        type3 = [font for font in fonts if font["type3"]]
        result["pdf_unembedded_font_count"] = len(unembedded)
        result["pdf_type3_font_count"] = len(type3)
        if require_embedded_fonts and unembedded:
            names = sorted({font["base_font"] for font in unembedded})
            add_issue(result, f"PDF contains unembedded fonts: {names}", error=True)
        elif unembedded:
            add_issue(result, "PDF contains one or more unembedded fonts")
        if forbid_type3_fonts and type3:
            names = sorted({font["base_font"] for font in type3})
            add_issue(result, f"PDF contains forbidden Type 3 fonts: {names}", error=True)
        elif type3:
            add_issue(result, "PDF contains Type 3 fonts", strict=strict)

        result["pdf_transparency"] = transparency
        result["pdf_has_transparency"] = bool(transparency)
        if forbid_transparency and transparency:
            add_issue(result, "PDF uses transparency, soft masks, or non-normal blending", error=True)

        result["pdf_embedded_rasters"] = images
        effective_dpi_values: list[float] = []
        for image in images:
            for use in image["uses"]:
                values = [value for value in use["effective_dpi"] if value is not None]
                if values:
                    effective_dpi_values.append(min(values))
        result["pdf_min_embedded_raster_effective_dpi"] = (
            min(effective_dpi_values) if effective_dpi_values else None
        )
        if effective_dpi_values and dpi_is_below(
            min(effective_dpi_values), min_effective_dpi
        ):
            add_issue(
                result,
                f"PDF contains an embedded raster below {min_effective_dpi:g} effective DPI: "
                f"{min(effective_dpi_values):.3f}",
                strict=strict,
            )
    except ImportError:
        add_issue(
            result,
            "pypdf is not installed; skipped PDF page, font, transparency, and image inspection",
            strict=strict,
        )
    except Exception as exc:  # noqa: BLE001
        add_issue(result, f"could not inspect PDF: {exc}", error=True)


SVG_LENGTH_RE = re.compile(
    r"^\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)\s*(px|pt|pc|mm|cm|in)?\s*$"
)


def svg_length_mm(value: str | None) -> float | None:
    if value is None:
        return None
    match = SVG_LENGTH_RE.match(value)
    if not match:
        return None
    number = float(match.group(1))
    unit = match.group(2) or "px"
    factors = {
        "px": 25.4 / 96.0,
        "pt": 25.4 / 72.0,
        "pc": 25.4 / 6.0,
        "mm": 1.0,
        "cm": 10.0,
        "in": 25.4,
    }
    return number * factors[unit]


def svg_has_transparency(root: ET.Element) -> bool:
    properties = ("opacity", "fill-opacity", "stroke-opacity")
    for element in root.iter():
        for prop in properties:
            value = finite_float(element.attrib.get(prop))
            if value is not None and value < 0.999999:
                return True
        style = element.attrib.get("style", "")
        for prop in properties:
            match = re.search(rf"(?:^|;)\s*{re.escape(prop)}\s*:\s*([^;]+)", style)
            if match:
                value = finite_float(match.group(1).strip())
                if value is not None and value < 0.999999:
                    return True
    return False

def inspect_svg(
    path: Path,
    result: dict[str, Any],
    *,
    expected_width_mm: float | None,
    expected_height_mm: float | None,
    size_tolerance_mm: float,
    svg_text_policy: str,
    forbid_transparency: bool,
    strict: bool,
) -> None:
    try:
        root = ET.parse(path).getroot()
        if not root.tag.lower().endswith("svg"):
            add_issue(result, "root SVG tag not found", strict=strict)
            return
        width_raw = root.attrib.get("width")
        height_raw = root.attrib.get("height")
        viewbox_raw = root.attrib.get("viewBox") or root.attrib.get("viewbox")
        width_mm = svg_length_mm(width_raw)
        height_mm = svg_length_mm(height_raw)
        result["svg_width"] = width_raw
        result["svg_height"] = height_raw
        result["svg_physical_size_mm"] = (
            [width_mm, height_mm] if width_mm is not None and height_mm is not None else None
        )
        if viewbox_raw:
            try:
                result["svg_viewbox"] = [
                    float(value) for value in viewbox_raw.replace(",", " ").split()
                ]
            except ValueError:
                result["svg_viewbox"] = viewbox_raw
                add_issue(result, "SVG viewBox could not be parsed", strict=strict)
        else:
            result["svg_viewbox"] = None
            add_issue(result, "SVG has no viewBox", strict=strict)

        check_expected_size(
            result,
            result["svg_physical_size_mm"],
            expected_width_mm=expected_width_mm,
            expected_height_mm=expected_height_mm,
            tolerance_mm=size_tolerance_mm,
            source="SVG width/height",
        )

        text_count = sum(1 for element in root.iter() if element.tag.lower().endswith("text"))
        result["svg_text_element_count"] = text_count
        result["svg_text_policy"] = svg_text_policy
        if svg_text_policy == "text" and text_count == 0:
            add_issue(
                result,
                "SVG text policy requires text elements, but all text appears outlined",
                error=True,
            )
        if svg_text_policy == "paths" and text_count > 0:
            add_issue(
                result,
                "SVG text policy requires outlined/path text, but text elements remain",
                error=True,
            )

        has_transparency = svg_has_transparency(root)
        result["svg_has_transparency"] = has_transparency
        if forbid_transparency and has_transparency:
            add_issue(result, "SVG uses opacity below 1", error=True)
    except (OSError, ET.ParseError) as exc:
        add_issue(result, f"could not read SVG: {exc}", error=True)


def inspect_eps(path: Path, result: dict[str, Any], *, strict: bool) -> None:
    try:
        with path.open("rb") as handle:
            header = handle.read(16)
        if not header.startswith((b"%!PS-Adobe", b"%!PS")):
            add_issue(result, "EPS/PostScript header is missing or invalid", strict=strict)
    except OSError as exc:
        add_issue(result, f"could not read EPS header: {exc}", error=True)


def inspect_file(
    path: Path,
    *,
    min_effective_dpi: float,
    min_bytes: int,
    max_bytes: int | None,
    min_width_px: int | None,
    min_height_px: int | None,
    allow_formats: set[str] | None,
    expected_width_mm: float | None,
    expected_height_mm: float | None,
    size_tolerance_mm: float,
    require_embedded_fonts: bool,
    forbid_type3_fonts: bool,
    forbid_transparency: bool,
    forbid_alpha: bool,
    require_tiff_mode: str | None,
    require_tiff_compression: str | None,
    svg_text_policy: str,
    strict: bool,
) -> dict[str, Any]:
    suffix = path.suffix.lower()
    canonical = canonical_ext(suffix)
    result: dict[str, Any] = {
        "path": str(path),
        "exists": path.exists(),
        "extension": suffix,
        "canonical_format": canonical,
        "warnings": [],
        "errors": [],
    }

    if not path.exists():
        add_issue(result, "missing file", error=True)
        result["ok"] = False
        return result

    size = path.stat().st_size
    result["size_bytes"] = int(size)
    if size < min_bytes:
        add_issue(
            result,
            f"file is suspiciously small: {size} bytes < {min_bytes} bytes",
            strict=strict,
        )
    if max_bytes is not None and size > max_bytes:
        add_issue(
            result,
            f"file is very large: {size} bytes > {max_bytes} bytes; verify DPI, "
            "compression, and rasterization of dense layers",
        )
    if allow_formats and canonical not in allow_formats:
        add_issue(
            result,
            f"format {canonical} is not allowed; allowed formats are {sorted(allow_formats)}",
            error=True,
        )

    if suffix not in KNOWN_EXTS:
        add_issue(result, "unrecognized figure extension", error=True if strict else False)
    elif suffix in RASTER_EXTS:
        inspect_raster(
            path,
            result,
            min_effective_dpi=min_effective_dpi,
            min_width_px=min_width_px,
            min_height_px=min_height_px,
            expected_width_mm=expected_width_mm,
            expected_height_mm=expected_height_mm,
            size_tolerance_mm=size_tolerance_mm,
            forbid_alpha=forbid_alpha,
            require_tiff_mode=require_tiff_mode,
            require_tiff_compression=require_tiff_compression,
            strict=strict,
        )
    elif suffix == ".pdf":
        inspect_pdf(
            path,
            result,
            min_effective_dpi=min_effective_dpi,
            expected_width_mm=expected_width_mm,
            expected_height_mm=expected_height_mm,
            size_tolerance_mm=size_tolerance_mm,
            require_embedded_fonts=require_embedded_fonts,
            forbid_type3_fonts=forbid_type3_fonts,
            forbid_transparency=forbid_transparency,
            strict=strict,
        )
    elif suffix == ".svg":
        inspect_svg(
            path,
            result,
            expected_width_mm=expected_width_mm,
            expected_height_mm=expected_height_mm,
            size_tolerance_mm=size_tolerance_mm,
            svg_text_policy=svg_text_policy,
            forbid_transparency=forbid_transparency,
            strict=strict,
        )
    elif suffix == ".eps":
        inspect_eps(path, result, strict=strict)

    result["ok"] = not result["errors"]
    return result


def audit_files(
    figures: list[Path] | tuple[Path, ...],
    *,
    allow_formats: set[str] | None = None,
    require_formats: set[str] | None = None,
    min_effective_dpi: float = 300.0,
    expected_width_mm: float | None = None,
    expected_height_mm: float | None = None,
    size_tolerance_mm: float = 0.5,
    min_bytes: int = 2048,
    max_bytes: int | None = None,
    min_width_px: int | None = None,
    min_height_px: int | None = None,
    require_embedded_fonts: bool = False,
    forbid_type3_fonts: bool = False,
    forbid_transparency: bool = False,
    forbid_alpha: bool = False,
    require_tiff_mode: str | None = None,
    require_tiff_compression: str | None = None,
    svg_text_policy: str = "any",
    strict: bool = False,
    fail_on_warning: bool = False,
) -> dict[str, Any]:
    """Audit saved figure artifacts through the stable Python API."""
    if min_effective_dpi < 0:
        raise ValueError("min_effective_dpi must be non-negative")
    if size_tolerance_mm < 0:
        raise ValueError("size_tolerance_mm must be non-negative")
    if svg_text_policy not in {"any", "text", "paths"}:
        raise ValueError("svg_text_policy must be 'any', 'text', or 'paths'")

    normalized_tiff_mode = normalize_tiff_mode(require_tiff_mode)
    normalized_tiff_compression = normalize_tiff_compression(require_tiff_compression)
    if require_tiff_mode is not None and normalized_tiff_mode is None:
        raise ValueError("require_tiff_mode must be a non-empty string")
    if require_tiff_compression is not None and normalized_tiff_compression is None:
        raise ValueError("require_tiff_compression must be a non-empty string")

    normalized_allow = (
        {canonical_ext(value) for value in allow_formats} if allow_formats else None
    )
    normalized_require = (
        {canonical_ext(value) for value in require_formats} if require_formats else None
    )
    paths = [Path(path) for path in figures]
    inspected = [
        inspect_file(
            path,
            min_effective_dpi=min_effective_dpi,
            min_bytes=min_bytes,
            max_bytes=max_bytes,
            min_width_px=min_width_px,
            min_height_px=min_height_px,
            allow_formats=normalized_allow,
            expected_width_mm=expected_width_mm,
            expected_height_mm=expected_height_mm,
            size_tolerance_mm=size_tolerance_mm,
            require_embedded_fonts=require_embedded_fonts,
            forbid_type3_fonts=forbid_type3_fonts,
            forbid_transparency=forbid_transparency,
            forbid_alpha=forbid_alpha,
            require_tiff_mode=normalized_tiff_mode,
            require_tiff_compression=normalized_tiff_compression,
            svg_text_policy=svg_text_policy,
            strict=strict,
        )
        for path in paths
    ]

    supplied_formats = {canonical_ext(path.suffix) for path in paths if path.exists()}
    missing_formats = sorted((normalized_require or set()) - supplied_formats)
    report_errors = (
        [f"required output formats are missing: {missing_formats}"]
        if missing_formats
        else []
    )
    warning_count = sum(len(item["warnings"]) for item in inspected)
    error_count = sum(len(item["errors"]) for item in inspected) + len(report_errors)
    return {
        "policy": {
            "allow_formats": sorted(normalized_allow) if normalized_allow else None,
            "require_formats": sorted(normalized_require) if normalized_require else None,
            "min_effective_dpi": min_effective_dpi,
            "dpi_comparison_tolerance": {
                "absolute": DPI_ABS_TOLERANCE,
                "relative": DPI_REL_TOLERANCE,
            },
            "expected_width_mm": expected_width_mm,
            "expected_height_mm": expected_height_mm,
            "size_tolerance_mm": size_tolerance_mm,
            "require_embedded_fonts": require_embedded_fonts,
            "forbid_type3_fonts": forbid_type3_fonts,
            "forbid_transparency": forbid_transparency,
            "forbid_alpha": forbid_alpha,
            "require_tiff_mode": normalized_tiff_mode,
            "require_tiff_compression": normalized_tiff_compression,
            "svg_text_policy": svg_text_policy,
            "strict": strict,
            "fail_on_warning": fail_on_warning,
        },
        "errors": report_errors,
        "summary": {
            "figure_count": len(inspected),
            "warning_count": warning_count,
            "error_count": error_count,
            "ok": error_count == 0 and not (fail_on_warning and warning_count),
        },
        "figures": inspected,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("figures", nargs="+", type=Path, help="Exported figure files to inspect")
    parser.add_argument("--json", type=Path, help="Optional JSON report path")
    parser.add_argument(
        "--allow-formats",
        help="Comma-separated allowed formats, e.g. pdf,tif,svg",
    )
    parser.add_argument(
        "--require-formats",
        help="Comma-separated formats that must all be present across the supplied files",
    )
    parser.add_argument(
        "--min-effective-dpi",
        "--min-dpi",
        dest="min_effective_dpi",
        type=float,
        default=300.0,
        help="Minimum raster or PDF-embedded-raster effective DPI (default: 300)",
    )
    parser.add_argument("--expected-width-mm", type=float, help="Expected final physical width")
    parser.add_argument("--expected-height-mm", type=float, help="Expected final physical height")
    parser.add_argument(
        "--size-tolerance-mm",
        type=float,
        default=0.5,
        help="Allowed physical-size difference per dimension (default: 0.5 mm)",
    )
    parser.add_argument("--min-bytes", type=int, default=2048, help="Minimum expected file size")
    parser.add_argument("--max-bytes", type=int, help="Warn when a file exceeds this size")
    parser.add_argument("--min-width-px", type=int, help="Optional minimum raster width")
    parser.add_argument("--min-height-px", type=int, help="Optional minimum raster height")
    parser.add_argument(
        "--require-embedded-fonts",
        action="store_true",
        help="Fail when a PDF uses an unembedded font",
    )
    parser.add_argument(
        "--forbid-type3-fonts",
        action="store_true",
        help="Fail when a PDF contains Type 3 fonts",
    )
    parser.add_argument(
        "--forbid-transparency",
        action="store_true",
        help="Fail when PDF/SVG transparency or soft masks are detected",
    )
    parser.add_argument(
        "--forbid-alpha",
        action="store_true",
        help="Fail when a raster image contains alpha/transparency",
    )
    parser.add_argument(
        "--require-tiff-mode",
        metavar="MODE",
        help="Fail when a TIFF does not use this Pillow color mode, e.g. RGB",
    )
    parser.add_argument(
        "--require-tiff-compression",
        metavar="COMPRESSION",
        help="Fail when a TIFF does not use this compression, e.g. LZW",
    )
    parser.add_argument(
        "--svg-text-policy",
        choices=("any", "text", "paths"),
        default="any",
        help="Require editable SVG text, outlined/path text, or accept either",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Upgrade delivery warnings such as low/missing DPI and invalid headers to errors",
    )
    parser.add_argument(
        "--fail-on-warning",
        action="store_true",
        help="Exit nonzero when any warning is present",
    )
    args = parser.parse_args()

    allow_formats = parse_formats(args.allow_formats)
    require_formats = parse_formats(args.require_formats)
    try:
        report = audit_files(
            args.figures,
            allow_formats=allow_formats,
            require_formats=require_formats,
            min_effective_dpi=args.min_effective_dpi,
            expected_width_mm=args.expected_width_mm,
            expected_height_mm=args.expected_height_mm,
            size_tolerance_mm=args.size_tolerance_mm,
            min_bytes=args.min_bytes,
            max_bytes=args.max_bytes,
            min_width_px=args.min_width_px,
            min_height_px=args.min_height_px,
            require_embedded_fonts=args.require_embedded_fonts,
            forbid_type3_fonts=args.forbid_type3_fonts,
            forbid_transparency=args.forbid_transparency,
            forbid_alpha=args.forbid_alpha,
            require_tiff_mode=args.require_tiff_mode,
            require_tiff_compression=args.require_tiff_compression,
            svg_text_policy=args.svg_text_policy,
            strict=args.strict,
            fail_on_warning=args.fail_on_warning,
        )
    except ValueError as exc:
        parser.error(str(exc))
    text = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(text, encoding="utf-8")
        print(f"wrote {args.json}")
    print(text)

    if not report["summary"]["ok"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
