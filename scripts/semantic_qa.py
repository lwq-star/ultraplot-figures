#!/usr/bin/env python3
"""Validate a figure against task, axes, encoding, and output evidence."""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any


INTENT_KEYS = ("figure_purpose", "reader_judgment")
BASE_REQUIRED_KEYS = ("target_filter", "panels", "encodings", "outputs")
EXPECTED_REQUIRED_KEYS = (
    "contract_version",
    *INTENT_KEYS,
    "requested_judgments",
    "evidence_map",
    "target_policy",
)
CONTRACT_VERSION = 2
EVIDENCE_KINDS = frozenset(
    {
        "comparison",
        "distribution",
        "model_diagnostic",
        "other",
        "relationship",
        "spatial_pattern",
        "statistical_result",
        "trend",
        "uncertainty",
    }
)
POSITION_LENGTH_TOKENS = frozenset(
    {"x", "y", "position", "length", "height", "count", "density", "frequency"}
)
LOW_PRECISION_TOKENS = frozenset(
    {"alpha", "area", "color", "colour", "hue", "marker", "opacity", "size"}
)
NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
}
PANEL_COUNT_PATTERN = re.compile(
    r"(?P<count>\d+|one|two|three|four|five|一|二|两|三|四|五)\s*"
    r"(?:个|幅|张)?\s*(?P<kind>小图|子图|面板|直方图|分布图|热图|箱线图|"
    r"散点图|折线图|small\s+plots?|side\s+panels?|subplots?|panels?|"
    r"plots?|histograms?|distribution\s+plots?|heatmaps?|boxplots?|"
    r"scatter\s+plots?|line\s+plots?)",
    re.IGNORECASE,
)
SUPPORTING_PANEL_PATTERN = re.compile(
    r"\b(?:histograms?|distribution\s+plots?|heatmaps?|boxplots?|"
    r"scatter\s+plots?|line\s+plots?)\b|直方图|分布图|热图|箱线图|散点图|折线图",
    re.IGNORECASE,
)
NEGATION_PATTERN = re.compile(
    r"\b(?:no|not|without|exclude|omit|avoid|do\s+not|don't)\b|"
    r"不要|不需要|无需|不含|省略|避免|禁止",
    re.IGNORECASE,
)
OUTPUT_SUFFIX_ROLES = {
    ".py": "python",
    ".pdf": "pdf",
    ".tif": "tiff",
    ".tiff": "tiff",
    ".png": "png",
    ".svg": "svg",
    ".json": "report",
    ".md": "report",
    ".txt": "report",
}
OUTPUT_ROLE_ALIASES = {
    "python": "python",
    "py": "python",
    "script": "python",
    "python_code": "python",
    "python_script": "python",
    "pdf": "pdf",
    "tif": "tiff",
    "tiff": "tiff",
    "png": "png",
    "preview": "png",
    "preview_png": "png",
    "svg": "svg",
    "report": "report",
}
OUTPUT_REQUEST_PATTERNS = {
    "python": re.compile(
        r"(?<![A-Za-z0-9_])python(?![A-Za-z0-9_])|"
        r"完整可运行的\s*(?:python\s*)?(?:代码|脚本)|"
        r"(?<![A-Za-z0-9_])\.py(?![A-Za-z0-9_])",
        re.IGNORECASE,
    ),
    "pdf": re.compile(r"(?<![A-Za-z0-9_])pdf(?![A-Za-z0-9_])", re.IGNORECASE),
    "tiff": re.compile(
        r"(?<![A-Za-z0-9_])(?:tif|tiff)(?![A-Za-z0-9_])", re.IGNORECASE
    ),
    "png": re.compile(
        r"(?<![A-Za-z0-9_])png(?![A-Za-z0-9_])|"
        r"(?<![A-Za-z0-9_])preview(?:\s+image)?(?![A-Za-z0-9_])|预览图?",
        re.IGNORECASE,
    ),
    "svg": re.compile(r"(?<![A-Za-z0-9_])svg(?![A-Za-z0-9_])", re.IGNORECASE),
    "report": re.compile(r"(?<![A-Za-z0-9_])report(?![A-Za-z0-9_])|报告文件", re.IGNORECASE),
}
ADAPTIVE_LAYOUT_ARGUMENTS = frozenset(
    {
        "bottom",
        "equal",
        "group",
        "hequal",
        "hgroup",
        "hpad",
        "hspace",
        "innerpad",
        "left",
        "outerpad",
        "pad",
        "panelpad",
        "right",
        "share",
        "space",
        "span",
        "tight",
        "top",
        "wequal",
        "wgroup",
        "wpad",
        "wspace",
    }
)


def _error(errors: list[str], message: str) -> None:
    errors.append(message)


def _validate_string_list(
    value: Any,
    name: str,
    errors: list[str],
    *,
    require_nonempty: bool = True,
) -> list[str]:
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        _error(errors, f"{name} must be a list of non-empty strings.")
        return []
    normalized = [item.strip() for item in value]
    if require_nonempty and not normalized:
        _error(errors, f"{name} must contain at least one entry.")
    if len(normalized) != len(set(normalized)):
        _error(errors, f"{name} contains duplicate entries: {normalized!r}.")
    return normalized


def _canonical_output_role(value: str) -> str | None:
    token = value.strip().lower().replace("-", "_").replace(" ", "_")
    if token in OUTPUT_ROLE_ALIASES:
        return OUTPUT_ROLE_ALIASES[token]
    return OUTPUT_SUFFIX_ROLES.get(Path(value).suffix.lower())


def _normalize_outputs(
    value: Any,
    name: str,
    errors: list[str],
    *,
    base_dir: Path | None = None,
    require_existing_paths: bool = False,
) -> tuple[list[str], list[str]]:
    items = _validate_string_list(value, name, errors)
    roles: list[str] = []
    for item in items:
        role = _canonical_output_role(item)
        if role is None:
            _error(
                errors,
                f"{name} entry {item!r} has no recognized deliverable role or file extension.",
            )
            continue
        roles.append(role)

        if require_existing_paths:
            path = Path(item)
            if not path.suffix:
                _error(errors, f"{name} entry {item!r} must be a real file path.")
                continue
            resolved = path if path.is_absolute() else (base_dir or Path.cwd()) / path
            if not resolved.is_file():
                _error(errors, f"Required output file does not exist: {resolved}.")

    return list(dict.fromkeys(roles)), items


def _validate_requested_judgments(
    value: Any,
    name: str,
    errors: list[str],
) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        _error(errors, f"{name} must be a non-empty list of judgment objects.")
        return []

    normalized: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_spans: set[str] = set()
    for index, item in enumerate(value):
        item_name = f"{name}[{index}]"
        if not isinstance(item, Mapping):
            _error(errors, f"{item_name} must be an object.")
            continue

        judgment_id = item.get("id")
        request_span = item.get("request_span")
        question = item.get("question")
        evidence_kind = item.get("evidence_kind")
        fields = _validate_string_list(item.get("fields"), f"{item_name}.fields", errors)
        for key, raw in (
            ("id", judgment_id),
            ("request_span", request_span),
            ("question", question),
            ("evidence_kind", evidence_kind),
        ):
            if not isinstance(raw, str) or not raw.strip():
                _error(errors, f"{item_name}.{key} must be a non-empty string.")

        if not isinstance(judgment_id, str) or not judgment_id.strip():
            continue
        judgment_id = judgment_id.strip()
        if judgment_id in seen_ids:
            _error(errors, f"{name} contains duplicate id {judgment_id!r}.")
        seen_ids.add(judgment_id)

        span = request_span.strip() if isinstance(request_span, str) else ""
        if span and span in seen_spans:
            _error(errors, f"{name} contains duplicate request_span {span!r}.")
        if span:
            seen_spans.add(span)

        kind = evidence_kind.strip().lower() if isinstance(evidence_kind, str) else ""
        if kind and kind not in EVIDENCE_KINDS:
            _error(
                errors,
                f"{item_name}.evidence_kind must be one of {sorted(EVIDENCE_KINDS)!r}.",
            )
        normalized.append(
            {
                "id": judgment_id,
                "request_span": span,
                "question": question.strip() if isinstance(question, str) else "",
                "evidence_kind": kind,
                "fields": fields,
            }
        )
    return normalized


def _validate_evidence_map(
    value: Any,
    name: str,
    judgments: list[dict[str, Any]],
    panels: list[str],
    encodings: Mapping[str, str],
    errors: list[str],
) -> dict[str, list[dict[str, Any]]]:
    if not isinstance(value, Mapping):
        _error(errors, f"{name} must map judgment ids to evidence entries.")
        return {}

    judgment_by_id = {item["id"]: item for item in judgments}
    extra_ids = sorted(set(value) - set(judgment_by_id))
    if extra_ids:
        _error(errors, f"{name} contains unknown judgment ids: {extra_ids!r}.")

    normalized: dict[str, list[dict[str, Any]]] = {}
    for judgment_id, judgment in judgment_by_id.items():
        entries = value.get(judgment_id)
        if not isinstance(entries, list) or not entries:
            _error(errors, f"{name}.{judgment_id} must contain at least one evidence entry.")
            normalized[judgment_id] = []
            continue

        normalized_entries: list[dict[str, Any]] = []
        mapped_fields: set[str] = set()
        for index, entry in enumerate(entries):
            entry_name = f"{name}.{judgment_id}[{index}]"
            if not isinstance(entry, Mapping):
                _error(errors, f"{entry_name} must be an object.")
                continue
            panel = entry.get("panel")
            if not isinstance(panel, str) or not panel.strip():
                _error(errors, f"{entry_name}.panel must be a non-empty string.")
                panel = ""
            else:
                panel = panel.strip()
                if panel not in panels:
                    _error(errors, f"{entry_name}.panel {panel!r} is not in expected.panels.")

            channels = _validate_string_list(
                entry.get("channels"), f"{entry_name}.channels", errors
            )
            for channel in channels:
                field = encodings.get(channel)
                if field is None:
                    _error(
                        errors,
                        f"{entry_name}.channels references unknown encoding {channel!r}.",
                    )
                else:
                    mapped_fields.add(field)
            justification = entry.get("justification", "")
            if not isinstance(justification, str):
                _error(errors, f"{entry_name}.justification must be a string when supplied.")
                justification = ""
            normalized_entries.append(
                {
                    "panel": panel,
                    "channels": channels,
                    "justification": justification.strip(),
                }
            )

        missing_fields = sorted(set(judgment["fields"]) - mapped_fields)
        if missing_fields:
            _error(
                errors,
                f"{name}.{judgment_id} does not map requested field(s) "
                f"{missing_fields!r} to evidence channels.",
            )
        normalized[judgment_id] = normalized_entries
    return normalized


def _validate_target_policy(
    value: Any,
    name: str,
    errors: list[str],
) -> dict[str, dict[str, Any]]:
    if not isinstance(value, Mapping) or not value:
        _error(errors, f"{name} must be a non-empty mapping of settings to value/source objects.")
        return {}
    normalized: dict[str, dict[str, Any]] = {}
    for raw_key, spec in value.items():
        if not isinstance(raw_key, str) or not raw_key.strip():
            _error(errors, f"{name} setting names must be non-empty strings.")
            continue
        key = raw_key.strip()
        if not isinstance(spec, Mapping):
            _error(errors, f"{name}.{key} must contain value and source.")
            continue
        if "value" not in spec:
            _error(errors, f"{name}.{key}.value is required, including when its value is null.")
        source = spec.get("source")
        if not isinstance(source, str) or not source.strip():
            _error(errors, f"{name}.{key}.source must be a non-empty provenance string.")
            source = ""
        normalized[key] = {"value": spec.get("value"), "source": source.strip()}
    return normalized


def _validate_contract_section(
    section: Any,
    name: str,
    errors: list[str],
    *,
    base_dir: Path | None = None,
    require_existing_outputs: bool = False,
    require_intent: bool = False,
) -> dict[str, Any]:
    if not isinstance(section, dict):
        _error(errors, f"{name} must be an object.")
        return {}
    for key in BASE_REQUIRED_KEYS:
        if key not in section:
            _error(errors, f"{name}.{key} is required.")

    contract_version: int | None = None
    requested_judgments: list[dict[str, Any]] = []
    evidence_map: dict[str, list[dict[str, Any]]] = {}
    target_policy: dict[str, dict[str, Any]] = {}
    if require_intent:
        for key in EXPECTED_REQUIRED_KEYS:
            if key not in section:
                _error(errors, f"{name}.{key} is required for an expected contract.")
        raw_version = section.get("contract_version")
        if (
            not isinstance(raw_version, int)
            or isinstance(raw_version, bool)
            or raw_version != CONTRACT_VERSION
        ):
            _error(
                errors,
                f"{name}.contract_version must be the integer {CONTRACT_VERSION}.",
            )
        else:
            contract_version = raw_version

    intent: dict[str, str] = {}
    if require_intent:
        for key in INTENT_KEYS:
            value = section.get(key)
            if not isinstance(value, str) or not value.strip():
                _error(errors, f"{name}.{key} must be a non-empty string.")
                intent[key] = ""
            else:
                intent[key] = value.strip()

    target_filter = section.get("target_filter")
    if target_filter is not None:
        if not isinstance(target_filter, dict):
            _error(errors, f"{name}.target_filter must be an object or null.")
        elif not target_filter:
            _error(errors, f"{name}.target_filter cannot be an empty object.")

    panels = _validate_string_list(section.get("panels"), f"{name}.panels", errors)
    output_roles, output_items = _normalize_outputs(
        section.get("outputs"),
        f"{name}.outputs",
        errors,
        base_dir=base_dir,
        require_existing_paths=require_existing_outputs,
    )

    encodings = section.get("encodings")
    if (
        not isinstance(encodings, dict)
        or not encodings
        or not all(
            isinstance(channel, str)
            and channel.strip()
            and isinstance(field, str)
            and field.strip()
            for channel, field in encodings.items()
        )
    ):
        _error(
            errors,
            f"{name}.encodings must be a non-empty mapping of channels to fields.",
        )
        encodings = {}

    if require_intent:
        requested_judgments = _validate_requested_judgments(
            section.get("requested_judgments"),
            f"{name}.requested_judgments",
            errors,
        )
        evidence_map = _validate_evidence_map(
            section.get("evidence_map"),
            f"{name}.evidence_map",
            requested_judgments,
            panels,
            encodings,
            errors,
        )
        target_policy = _validate_target_policy(
            section.get("target_policy"),
            f"{name}.target_policy",
            errors,
        )

    return {
        "contract_version": contract_version,
        **intent,
        "target_filter": target_filter,
        "panels": panels,
        "encodings": encodings,
        "outputs": output_roles,
        "output_items": output_items,
        "requested_judgments": requested_judgments,
        "evidence_map": evidence_map,
        "target_policy": target_policy,
    }


def _validate_counts(actual: dict[str, Any], errors: list[str]) -> None:
    counts = actual.get("counts")
    if actual.get("target_filter") is None and counts is None:
        return
    if not isinstance(counts, dict):
        _error(errors, "actual.counts is required when a target filter is active.")
        return

    required = ("input", "retained", "excluded")
    for key in required:
        value = counts.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            _error(errors, f"actual.counts.{key} must be a non-negative integer.")
    if all(
        isinstance(counts.get(key), int) and not isinstance(counts.get(key), bool)
        for key in required
    ):
        if counts["input"] != counts["retained"] + counts["excluded"]:
            _error(errors, "actual.counts.input must equal retained + excluded.")

    excluded_by_class = counts.get("excluded_by_class")
    if isinstance(counts.get("excluded"), int) and counts["excluded"] > 0:
        if excluded_by_class is None:
            _error(
                errors,
                "actual.counts.excluded_by_class is required when records are excluded.",
            )
            return
    if excluded_by_class is not None:
        if not isinstance(excluded_by_class, dict) or not all(
            isinstance(key, str)
            and key.strip()
            and isinstance(value, int)
            and not isinstance(value, bool)
            and value >= 0
            for key, value in excluded_by_class.items()
        ):
            _error(
                errors,
                "actual.counts.excluded_by_class must map classes to non-negative integers.",
            )
        elif isinstance(counts.get("excluded"), int):
            if sum(excluded_by_class.values()) != counts["excluded"]:
                _error(
                    errors,
                    "excluded_by_class values must sum to actual.counts.excluded.",
                )


def _number_value(token: str) -> int:
    return int(token) if token.isdigit() else NUMBER_WORDS[token.lower()]


def _is_negated(text: str, start: int) -> bool:
    return bool(NEGATION_PATTERN.search(text[max(0, start - 28) : start]))


def _requested_panel_floor(text: str) -> int:
    lower = text.lower()
    map_matches = [
        match
        for match in re.finditer(r"\bmap\b|地图|主图|main\s+(?:plot|panel)", lower)
        if not _is_negated(lower, match.start())
    ]
    has_main_figure = bool(map_matches)
    minimum = 1 if has_main_figure else 0

    for match in PANEL_COUNT_PATTERN.finditer(text):
        if _is_negated(lower, match.start()):
            continue
        count = _number_value(match.group("count"))
        kind = match.group("kind").lower()
        is_supporting = any(
            token in kind
            for token in (
                "小图",
                "直方图",
                "分布图",
                "热图",
                "箱线图",
                "散点图",
                "折线图",
                "small",
                "side",
                "histogram",
                "distribution",
                "heatmap",
                "boxplot",
                "scatter",
                "line",
            )
        )
        if has_main_figure and is_supporting:
            count += 1
        minimum = max(minimum, count)

    supporting_count = 0
    for match in SUPPORTING_PANEL_PATTERN.finditer(text):
        if _is_negated(lower, match.start()):
            continue
        supporting_count += 2 if match.group(0).lower().endswith("s") else 1
    if supporting_count:
        minimum = max(minimum, supporting_count + (1 if has_main_figure else 0))
    return minimum


def _requested_output_roles(text: str) -> list[str]:
    lower = text.lower()
    requested: list[str] = []
    for role, pattern in OUTPUT_REQUEST_PATTERNS.items():
        for match in pattern.finditer(lower):
            if not _is_negated(lower, match.start()):
                requested.append(role)
                break
    return requested


def _normalized_request_text(value: str) -> str:
    return " ".join(value.casefold().split())


def _channel_evidence_strength(channel: str) -> str:
    tokens = {
        token
        for token in re.split(r"[^a-z0-9]+", channel.casefold())
        if token
    }
    if tokens & POSITION_LENGTH_TOKENS:
        return "position_or_length"
    if tokens & LOW_PRECISION_TOKENS:
        return "area_or_color"
    return "other"


def _audit_request_text(
    request_text: Any,
    expected: dict[str, Any],
    errors: list[str],
    warnings: list[str],
) -> dict[str, Any]:
    if not isinstance(request_text, str) or not request_text.strip():
        _error(errors, "request_text must contain the original user request.")
        return {
            "minimum_panel_count": None,
            "requested_outputs": [],
            "judgment_coverage": [],
        }

    text = request_text.strip()
    minimum_panel_count = _requested_panel_floor(text)
    if minimum_panel_count and len(expected.get("panels", [])) < minimum_panel_count:
        _error(
            errors,
            "The original request implies at least "
            f"{minimum_panel_count} panels, but expected.panels contains "
            f"{len(expected.get('panels', []))}.",
        )

    requested_outputs = _requested_output_roles(text)
    expected_outputs = set(expected.get("outputs", []))
    for role in requested_outputs:
        if role not in expected_outputs:
            _error(
                errors,
                f"The original request requires {role}, but expected.outputs omits it.",
            )

    normalized_request = _normalized_request_text(text)
    judgment_coverage: list[dict[str, Any]] = []
    evidence_map = expected.get("evidence_map", {})
    for judgment in expected.get("requested_judgments", []):
        judgment_id = judgment["id"]
        request_span = judgment["request_span"]
        span_found = _normalized_request_text(request_span) in normalized_request
        if not span_found:
            _error(
                errors,
                f"expected.requested_judgments id {judgment_id!r} uses request_span "
                f"{request_span!r}, which is not present in the original request.",
            )

        entries = evidence_map.get(judgment_id, [])
        channel_strengths = [
            _channel_evidence_strength(channel)
            for entry in entries
            for channel in entry.get("channels", [])
        ]
        has_position_or_length = "position_or_length" in channel_strengths
        justified = any(entry.get("justification") for entry in entries)
        if (
            judgment.get("evidence_kind")
            in {"comparison", "distribution", "relationship", "trend"}
            and not has_position_or_length
            and not justified
        ):
            warnings.append(
                f"Judgment {judgment_id!r} requests {judgment['evidence_kind']} evidence "
                "but is supported only by area/color or unspecified channels. Add "
                "position/length evidence or record a request-specific justification."
            )
        judgment_coverage.append(
            {
                "id": judgment_id,
                "request_span": request_span,
                "request_span_found": span_found,
                "evidence_kind": judgment.get("evidence_kind"),
                "channels": [
                    channel
                    for entry in entries
                    for channel in entry.get("channels", [])
                ],
                "has_position_or_length": has_position_or_length,
                "justified": justified,
            }
        )

    return {
        "minimum_panel_count": minimum_panel_count or None,
        "requested_outputs": requested_outputs,
        "judgment_coverage": judgment_coverage,
    }


def _finish_report(report: dict[str, Any]) -> dict[str, Any]:
    errors = report["errors"]
    warnings = report["warnings"]
    report["summary"] = {
        "error_count": len(errors),
        "warning_count": len(warnings),
        "ok": not errors,
    }
    report["ok"] = not errors
    return report


def audit_task_contract(
    payload: dict[str, Any],
    *,
    base_dir: Path | None = None,
    require_actual_files: bool = False,
) -> dict[str, Any]:
    """Compare expected and actual serializable task facts."""
    errors: list[str] = []
    warnings: list[str] = []

    expected = _validate_contract_section(
        payload.get("expected"),
        "expected",
        errors,
        require_intent=True,
    )
    actual_source = payload.get("actual") or {}
    actual = _validate_contract_section(
        actual_source,
        "actual",
        errors,
        base_dir=base_dir,
        require_existing_outputs=require_actual_files,
    )
    _validate_counts(actual_source, errors)
    if isinstance(actual_source.get("counts"), dict):
        actual["counts"] = actual_source["counts"]
    request_checks = _audit_request_text(
        payload.get("request_text"), expected, errors, warnings
    )

    if expected and actual:
        if expected["target_filter"] != actual["target_filter"]:
            _error(
                errors,
                "Target-filter mismatch: "
                f"expected {expected['target_filter']!r}, "
                f"got {actual['target_filter']!r}.",
            )
        if expected["panels"] != actual["panels"]:
            _error(
                errors,
                "Panel mismatch: "
                f"expected {expected['panels']!r}, got {actual['panels']!r}.",
            )
        for channel, expected_field in expected["encodings"].items():
            actual_field = actual["encodings"].get(channel)
            if actual_field != expected_field:
                _error(
                    errors,
                    f"Encoding mismatch for {channel!r}: "
                    f"expected {expected_field!r}, got {actual_field!r}.",
                )
        missing_outputs = sorted(set(expected["outputs"]) - set(actual["outputs"]))
        if missing_outputs:
            _error(errors, f"Missing requested outputs: {missing_outputs!r}.")

    return _finish_report(
        {
            "expected": expected,
            "actual": actual,
            "request_checks": request_checks,
            "errors": errors,
            "warnings": warnings,
        }
    )


def _values_match(actual: Any, expected: Any) -> bool:
    import numpy as np

    actual_array = np.ma.getdata(np.asanyarray(actual))
    expected_array = np.ma.getdata(np.asanyarray(expected))
    if actual_array.shape != expected_array.shape:
        return False
    if actual_array.dtype.kind in "biufc" and expected_array.dtype.kind in "biufc":
        return bool(np.allclose(actual_array, expected_array, equal_nan=True))
    return bool(np.array_equal(actual_array, expected_array))


def _infer_encoding_kind(channel: str, evidence: dict[str, Any]) -> str:
    if isinstance(evidence.get("kind"), str):
        return evidence["kind"].strip().lower()
    name = channel.lower()
    if "color" in name or "colour" in name:
        return "color"
    if "size" in name or "area" in name:
        return "size"
    if name.endswith(".x") or name.endswith(" x") or name.startswith("x "):
        return "x"
    if name.endswith(".y") or name.endswith(" y") or name.startswith("y "):
        return "y"
    return "generic"


def _artist_values(artist: Any, kind: str) -> Any | None:
    if kind == "color" and hasattr(artist, "get_array"):
        return artist.get_array()
    if kind == "x":
        if hasattr(artist, "get_xdata"):
            return artist.get_xdata()
        if hasattr(artist, "get_offsets"):
            return artist.get_offsets()[:, 0]
    if kind == "y":
        if hasattr(artist, "get_ydata"):
            return artist.get_ydata()
        if hasattr(artist, "get_offsets"):
            return artist.get_offsets()[:, 1]
    return None


def _find_ultraplot_layout_overrides(
    source: str,
    *,
    source_path: str = "<string>",
) -> list[dict[str, Any]]:
    """Return explicit adaptive-layout arguments on UltraPlot subplots calls."""
    tree = ast.parse(source, filename=source_path)
    module_aliases: set[str] = set()
    direct_subplots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "ultraplot" or alias.name.startswith("ultraplot."):
                    module_aliases.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module == "ultraplot" or node.module.startswith("ultraplot."):
                for alias in node.names:
                    if alias.name == "subplots":
                        direct_subplots.add(alias.asname or alias.name)

    findings: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        is_subplots = (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "subplots"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id in module_aliases
        ) or (
            isinstance(node.func, ast.Name) and node.func.id in direct_subplots
        )
        if not is_subplots:
            continue
        for keyword in node.keywords:
            if keyword.arg in ADAPTIVE_LAYOUT_ARGUMENTS:
                findings.append(
                    {
                        "path": source_path,
                        "line": int(getattr(keyword, "lineno", node.lineno)),
                        "argument": keyword.arg,
                    }
                )
    return sorted(findings, key=lambda item: (item["line"], item["argument"]))


def _registered_subplot_titles(axes_registry: Mapping[str, Any]) -> list[dict[str, str]]:
    titles: list[dict[str, str]] = []
    for role, axis in axes_registry.items():
        get_title = getattr(axis, "get_title", None)
        if not callable(get_title):
            continue
        for location in ("left", "center", "right"):
            try:
                text = get_title(loc=location)
            except TypeError:
                if location != "center":
                    continue
                text = get_title()
            text = str(text).strip()
            if text:
                titles.append({"panel": str(role), "location": location, "text": text})
    return titles


def audit_figure_contract(
    fig: Any,
    expected: dict[str, Any],
    axes_registry: dict[str, Any],
    encoding_evidence: dict[str, dict[str, Any]],
    *,
    request_text: str,
    target_filter: dict[str, Any] | None,
    counts: dict[str, Any] | None,
    output_paths: list[str | Path],
    allow_subplot_titles: bool = False,
    layout_override_reasons: Mapping[str, str] | None = None,
    require_output_files: bool = True,
) -> dict[str, Any]:
    """Bind semantic QA to the live figure, source, artists, values, and files.

    Set ``require_output_files=False`` during draft QA before production artifacts
    are written. Final submission QA must keep the default ``True`` value.
    """
    errors: list[str] = []

    if not isinstance(axes_registry, dict) or not axes_registry:
        _error(errors, "axes_registry must map panel roles to live axes.")
        axes_registry = {}
    panel_roles = list(axes_registry)
    registered_axes = list(axes_registry.values())
    if len({id(axis) for axis in registered_axes}) != len(registered_axes):
        _error(errors, "axes_registry must use a distinct axes object for every panel role.")
    figure_axes = list(getattr(fig, "axes", []))
    for role, axis in axes_registry.items():
        if axis not in figure_axes:
            _error(errors, f"Panel {role!r} is not backed by an axes in fig.axes.")
        if hasattr(axis, "get_visible") and not axis.get_visible():
            _error(errors, f"Panel {role!r} is not visible.")

    subplot_titles = _registered_subplot_titles(axes_registry)
    if subplot_titles and not allow_subplot_titles:
        details = ", ".join(
            f"{item['panel']!r}={item['text']!r}" for item in subplot_titles
        )
        _error(
            errors,
            "Unexpected subplot title(s): "
            f"{details}. Remove them or set allow_subplot_titles=True only when "
            "the request or panel semantics requires titles.",
        )

    if layout_override_reasons is None:
        normalized_reasons: dict[str, str] = {}
    elif isinstance(layout_override_reasons, Mapping):
        normalized_reasons = {
            str(key): value.strip()
            for key, value in layout_override_reasons.items()
            if isinstance(value, str) and value.strip()
        }
    else:
        _error(errors, "layout_override_reasons must be a mapping of argument to reason.")
        normalized_reasons = {}

    layout_overrides: list[dict[str, Any]] = []
    for raw_path in output_paths:
        source_path = Path(raw_path)
        if source_path.suffix.lower() != ".py":
            continue
        if not source_path.is_absolute():
            source_path = Path.cwd() / source_path
        if not source_path.is_file():
            continue
        try:
            findings = _find_ultraplot_layout_overrides(
                source_path.read_text(encoding="utf-8"),
                source_path=str(source_path),
            )
        except (OSError, UnicodeError, SyntaxError) as exc:
            _error(errors, f"Could not audit layout policy in {source_path}: {exc}")
            continue
        for finding in findings:
            argument = finding["argument"]
            reason = normalized_reasons.get(argument, "")
            finding["reason"] = reason
            finding["justified"] = bool(reason)
            layout_overrides.append(finding)
            if not reason:
                _error(
                    errors,
                    f"{source_path}:{finding['line']}: UltraPlot adaptive-layout "
                    f"argument {argument!r} overrides the default. Remove it from "
                    "the first render or provide a concrete layout_override_reasons "
                    "entry for a visible defect or explicit target requirement.",
                )

    actual_encodings: dict[str, str] = {}
    evidence_summary: dict[str, Any] = {}
    registered_ids = {id(axis) for axis in registered_axes}
    if not isinstance(encoding_evidence, dict) or not encoding_evidence:
        _error(errors, "encoding_evidence must bind channels to live axes/artists and values.")
        encoding_evidence = {}
    for channel, evidence in encoding_evidence.items():
        if not isinstance(evidence, dict):
            _error(errors, f"Encoding evidence for {channel!r} must be an object.")
            continue
        field = evidence.get("field")
        if not isinstance(field, str) or not field.strip():
            _error(errors, f"Encoding evidence for {channel!r} needs a non-empty field.")
            continue
        field = field.strip()
        actual_encodings[channel] = field

        axis = evidence.get("axis")
        artist = evidence.get("artist")
        artist_axis = getattr(artist, "axes", None) if artist is not None else None
        owner_axis = axis if axis is not None else artist_axis
        if owner_axis is None or id(owner_axis) not in registered_ids:
            _error(
                errors,
                f"Encoding {channel!r} is not bound to a registered panel axes.",
            )
        if artist is not None and artist_axis is not None and axis is not None:
            if artist_axis is not axis:
                _error(errors, f"Encoding {channel!r} artist and axis disagree.")

        if "values" not in evidence:
            _error(errors, f"Encoding {channel!r} must include the plotted source values.")
            values = None
        else:
            values = evidence["values"]
            try:
                if len(values) == 0:
                    _error(errors, f"Encoding {channel!r} has no source values.")
            except TypeError:
                pass

        kind = _infer_encoding_kind(channel, evidence)
        bound_values = _artist_values(artist, kind) if artist is not None else None
        if bound_values is not None and values is not None:
            if not _values_match(bound_values, values):
                _error(
                    errors,
                    f"Encoding {channel!r} artist data do not match its declared values.",
                )
        evidence_summary[channel] = {
            "field": field,
            "kind": kind,
            "panel_bound": owner_axis is not None and id(owner_axis) in registered_ids,
            "artist_values_checked": bound_values is not None,
        }

    actual = {
        "target_filter": target_filter,
        "panels": panel_roles,
        "encodings": actual_encodings,
        "outputs": [str(path) for path in output_paths],
    }
    if counts is not None:
        actual["counts"] = counts
    report = audit_task_contract(
        {"request_text": request_text, "expected": expected, "actual": actual},
        base_dir=Path.cwd(),
        require_actual_files=require_output_files,
    )
    report["errors"].extend(errors)
    report["figure_evidence"] = {
        "registered_panels": panel_roles,
        "figure_axes_count": len(figure_axes),
        "encodings": evidence_summary,
        "subplot_titles_allowed": bool(allow_subplot_titles),
        "subplot_titles": subplot_titles,
        "layout_policy": {
            "adaptive_arguments": sorted(ADAPTIVE_LAYOUT_ARGUMENTS),
            "overrides": layout_overrides,
        },
    }
    return _finish_report(report)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare expected and actual figure-task semantics."
    )
    parser.add_argument(
        "contract",
        type=Path,
        help="JSON file with request_text plus expected and actual sections.",
    )
    parser.add_argument(
        "--json",
        dest="json_path",
        type=Path,
        help="Write the QA report to this path.",
    )
    parser.add_argument(
        "--no-check-files",
        action="store_true",
        help="Do not require actual.outputs paths to exist.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    try:
        payload = json.loads(args.contract.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "errors": [str(exc)]}, indent=2))
        return 2
    if not isinstance(payload, dict):
        print(
            json.dumps(
                {"ok": False, "errors": ["Contract root must be an object."]},
                indent=2,
            )
        )
        return 2

    report = audit_task_contract(
        payload,
        base_dir=args.contract.parent,
        require_actual_files=not args.no_check_files,
    )
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)
    if args.json_path:
        args.json_path.parent.mkdir(parents=True, exist_ok=True)
        args.json_path.write_text(rendered + "\n", encoding="utf-8")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
