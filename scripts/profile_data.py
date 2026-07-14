#!/usr/bin/env python
"""Profile a tabular dataset for scientific chart selection.

This script is intentionally conservative. It reports data shape, column roles,
missingness, duplicates, group sizes, numeric ranges, suspicious values, and simple
chart-selection hints. It does not perform scientific analysis.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import warnings
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

HARD_ID_NAME_RE = re.compile(
    r"(^|[_\-\s])(id|ids|uuid|accession|barcode|index|row)([_\-\s]|$)",
    re.IGNORECASE,
)
SOFT_ID_NAME_RE = re.compile(
    r"(^|[_\-\s])(sample|subject|patient|gene|transcript|protein|station|site)([_\-\s]|$)",
    re.IGNORECASE,
)
LAT_NAMES = {"lat", "latitude", "y_lat", "lat_deg", "decimal_latitude"}
LON_NAMES = {"lon", "long", "longitude", "x_lon", "lon_deg", "decimal_longitude"}
YEAR_NAMES = {"year", "yr", "年份"}
PROP_NAME_RE = re.compile(r"(prop|proportion|ratio|fraction|rate|pct|percent|percentage|百分比|比例)", re.IGNORECASE)


def clean_name(name: object) -> str:
    return str(name).strip().lower()


def finite_numeric(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    return values.replace([np.inf, -np.inf], np.nan)


def is_integer_like(values: pd.Series) -> bool:
    vals = values.dropna()
    if vals.empty:
        return False
    return bool(np.all(np.isclose(vals, np.round(vals))))


def is_latitude(name: object, values: pd.Series) -> bool:
    cname = clean_name(name)
    vals = values.dropna()
    return cname in LAT_NAMES and not vals.empty and bool(vals.between(-90, 90).all())


def is_longitude(name: object, values: pd.Series) -> bool:
    cname = clean_name(name)
    vals = values.dropna()
    if cname not in LON_NAMES or vals.empty:
        return False
    return bool(vals.between(-180, 180).all() or vals.between(0, 360).all())


def is_year_like(name: object, values: pd.Series) -> bool:
    vals = values.dropna()
    if vals.empty or not is_integer_like(vals):
        return False
    cname = clean_name(name)
    in_range = vals.between(1800, 2100).mean() >= 0.95
    return bool(in_range and (cname in YEAR_NAMES or vals.nunique(dropna=True) <= 400))


def is_identifier_like(name: object, series: pd.Series, values: pd.Series | None = None) -> bool:
    non_null = series.dropna()
    if non_null.empty:
        return False
    cname = clean_name(name)
    unique_ratio = non_null.nunique(dropna=True) / len(non_null)

    # Hard ID tokens are explicit identifiers. Soft tokens such as ``site`` or
    # ``station`` are often legitimate grouping variables, so require high
    # cardinality before excluding them from chart-selection hints.
    if HARD_ID_NAME_RE.search(cname):
        return True
    if SOFT_ID_NAME_RE.search(cname) and unique_ratio > 0.8:
        return True

    if values is not None:
        vals = values.dropna()
        # Common row-number or integer key pattern.
        if unique_ratio > 0.98 and is_integer_like(vals):
            sorted_vals = np.sort(vals.to_numpy(dtype=float))
            if len(sorted_vals) > 2:
                diffs = np.diff(sorted_vals)
                if np.allclose(diffs, diffs[0]):
                    return True
    else:
        as_text = non_null.astype(str)
        avg_len = as_text.str.len().mean()
        if unique_ratio > 0.95 and avg_len <= 80:
            return True
    return False


def is_proportion_like(name: object, values: pd.Series) -> bool:
    vals = values.dropna()
    if vals.empty:
        return False
    cname = clean_name(name)
    by_name = bool(PROP_NAME_RE.search(cname))
    # A [0, 1] (or [0, 100]) range alone is ambiguous: normalized measures, scores,
    # indices, and probabilities all live there. Stay conservative and only label a
    # column as a proportion when the name signals it; otherwise leave it as a plain
    # numeric measure. This under-detects unnamed proportions by design, in exchange
    # for far fewer false positives in the chart-selection hints.
    if not by_name:
        return False
    return bool(vals.between(0, 1).all() or vals.between(0, 100).all())


def infer_role(series: pd.Series, name: object | None = None) -> str:
    col_name = series.name if name is None else name
    non_null = series.dropna()
    if non_null.empty:
        return "empty"

    unique = non_null.nunique(dropna=True)
    if unique == 1:
        return "constant"

    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"

    if pd.api.types.is_numeric_dtype(series):
        numeric = finite_numeric(series)
        finite = numeric.dropna()
        if finite.empty:
            return "numeric-invalid"
        if is_latitude(col_name, finite):
            return "latitude"
        if is_longitude(col_name, finite):
            return "longitude"
        if is_year_like(col_name, finite):
            return "year"
        if is_identifier_like(col_name, series, finite):
            return "identifier"
        if is_proportion_like(col_name, finite):
            return "proportion"
        if unique <= min(12, max(3, len(non_null) // 10)):
            return "numeric-discrete"
        return "numeric"

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        parsed = pd.to_datetime(non_null, errors="coerce")
    if parsed.notna().mean() >= 0.8:
        return "datetime-like"

    if is_identifier_like(col_name, series):
        return "identifier"

    if unique <= min(30, max(10, len(non_null) // 5)):
        return "categorical"
    return "text"


def numeric_summary(series: pd.Series) -> dict[str, Any]:
    s = finite_numeric(series).dropna()
    if s.empty:
        return {}
    q1 = float(s.quantile(0.25))
    q3 = float(s.quantile(0.75))
    iqr = q3 - q1
    if iqr > 0:
        outliers = int(((s < q1 - 1.5 * iqr) | (s > q3 + 1.5 * iqr)).sum())
    else:
        outliers = 0
    return {
        "min": float(s.min()),
        "q1": q1,
        "median": float(s.median()),
        "q3": q3,
        "max": float(s.max()),
        "mean": float(s.mean()),
        "std": float(s.std()) if len(s) > 1 else None,
        "zeros": int((s == 0).sum()),
        "negative": int((s < 0).sum()),
        "non_finite": int(pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan).isna().sum() - series.isna().sum()),
        "iqr_outliers": outliers,
    }


TEXT_SUFFIXES = {".tsv", ".tab", ".csv", ".txt"}
DEFAULT_ENCODINGS = ("utf-8-sig", "utf-8", "gb18030", "cp1252", "latin-1")
SNIFFER_DELIMITERS = ",\t;|"


def normalize_separator(value: str) -> str:
    return "\t" if value == r"\t" else value


def detect_text_format(
    path: Path,
    *,
    sep: str = "auto",
    encoding: str | None = None,
    sample_bytes: int = 65536,
) -> dict[str, Any]:
    """Detect a readable encoding and delimiter from a bounded head sample."""
    raw = path.read_bytes()[:sample_bytes]
    if not raw:
        raise SystemExit(f"Text file is empty: {path}")

    if encoding:
        candidates = (encoding,)
    elif raw.startswith(b"\xef\xbb\xbf"):
        candidates = DEFAULT_ENCODINGS
    else:
        # Avoid reporting every BOM-free UTF-8 file as utf-8-sig while preserving the
        # same conservative fallback chain after the first UTF-8 attempt.
        candidates = ("utf-8", "utf-8-sig", "gb18030", "cp1252", "latin-1")

    decoded: str | None = None
    encoding_used: str | None = None
    failures: list[str] = []
    for candidate in candidates:
        try:
            decoded = raw.decode(candidate)
            encoding_used = candidate
            break
        except UnicodeDecodeError as exc:
            failures.append(f"{candidate}: {exc}")
    if decoded is None or encoding_used is None:
        detail = "; ".join(failures)
        raise SystemExit(f"Could not decode {path}. Tried {list(candidates)}. {detail}")

    if sep != "auto":
        delimiter = normalize_separator(sep)
        delimiter_source = "explicit"
    else:
        try:
            dialect = csv.Sniffer().sniff(decoded, delimiters=SNIFFER_DELIMITERS)
            delimiter = dialect.delimiter
            delimiter_source = "csv.Sniffer"
        except csv.Error:
            delimiter = "\t" if path.suffix.lower() in {".tsv", ".tab"} else ","
            delimiter_source = "extension_fallback"

    return {
        "encoding": encoding_used,
        "encoding_candidates": list(candidates),
        "separator": delimiter,
        "separator_repr": "\\t" if delimiter == "\t" else delimiter,
        "separator_source": delimiter_source,
        "detection_sample_bytes": len(raw),
        "detection_scope": "file head bytes",
    }


def read_table(
    path: Path,
    sep: str = "auto",
    encoding: str | None = None,
    sheet: str | int | None = None,
    sample_rows: int | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    suffix = path.suffix.lower()
    sampling_method = "full_file" if sample_rows is None else "first_rows_head"
    sampling_note = (
        "All rows were profiled."
        if sample_rows is None
        else "Only the first/head rows were profiled; this is not a random or representative sample."
    )

    if suffix in {".xlsx", ".xls"}:
        try:
            df = pd.read_excel(
                path,
                sheet_name=0 if sheet is None else sheet,
                nrows=sample_rows,
            )
        except ImportError as exc:
            raise SystemExit(
                "Excel input requires an Excel engine such as openpyxl. Install it or convert the sheet to CSV/TSV."
            ) from exc
        metadata = {
            "format": suffix.lstrip("."),
            "encoding": None,
            "separator": None,
            "separator_repr": None,
            "separator_source": None,
        }
    elif suffix == ".parquet":
        full = pd.read_parquet(path)
        df = full if sample_rows is None else full.head(sample_rows)
        metadata = {
            "format": "parquet",
            "encoding": None,
            "separator": None,
            "separator_repr": None,
            "separator_source": None,
        }
        if sample_rows is not None:
            sampling_method = "first_rows_after_full_parquet_read"
            sampling_note = (
                "The Parquet file was read, then only the first/head rows were profiled; "
                "this is not a random or representative sample."
            )
    elif suffix in TEXT_SUFFIXES:
        detected = detect_text_format(path, sep=sep, encoding=encoding)
        df = pd.read_csv(
            path,
            sep=detected["separator"],
            encoding=detected["encoding"],
            nrows=sample_rows,
        )
        metadata = {"format": suffix.lstrip("."), **detected}
    else:
        raise SystemExit(
            f"Unsupported file type: {suffix}. Use CSV/TSV/TXT, Excel, Parquet, or convert the data first."
        )

    metadata.update(
        {
            "sample_rows_requested": sample_rows,
            "rows_profiled": int(df.shape[0]),
            "sampling_method": sampling_method,
            "sampling_note": sampling_note,
            "full_row_count_known": sample_rows is None,
        }
    )
    return df, metadata


def duplicate_text_headers(
    path: Path,
    *,
    separator: str | None,
    encoding: str | None,
) -> list[str]:
    if path.suffix.lower() not in TEXT_SUFFIXES or not separator or not encoding:
        return []
    try:
        with path.open("r", newline="", encoding=encoding) as handle:
            header = next(csv.reader(handle, delimiter=separator), [])
    except (OSError, StopIteration, UnicodeDecodeError):
        return []

    seen: set[str] = set()
    duplicates: list[str] = []
    for col in header:
        name = str(col)
        if name in seen and name not in duplicates:
            duplicates.append(name)
        seen.add(name)
    return duplicates


def possible_coordinate_pairs(roles: dict[str, str]) -> list[dict[str, str]]:
    lats = [c for c, r in roles.items() if r == "latitude"]
    lons = [c for c, r in roles.items() if r == "longitude"]
    return [{"lon": lon, "lat": lat} for lon in lons for lat in lats]


def build_profile(
    path: Path,
    sep: str = "auto",
    encoding: str | None = None,
    sheet: str | int | None = None,
    max_categories: int = 12,
    sample_rows: int | None = None,
) -> dict[str, Any]:
    df, read_metadata = read_table(
        path,
        sep=sep,
        encoding=encoding,
        sheet=sheet,
        sample_rows=sample_rows,
    )
    # pandas may mangle duplicate headers, for example x -> x.1, so inspect raw
    # delimited-file headers before falling back to parsed DataFrame columns.
    duplicate_columns = duplicate_text_headers(
        path,
        separator=read_metadata.get("separator"),
        encoding=read_metadata.get("encoding"),
    )
    if not duplicate_columns:
        duplicate_columns = [str(c) for c in df.columns[df.columns.duplicated()].tolist()]
    profile: dict[str, Any] = {
        "path": str(path),
        "rows": int(df.shape[0]),
        "rows_profiled": int(df.shape[0]),
        "read": read_metadata,
        "detected_encoding": read_metadata.get("encoding"),
        "detected_separator": read_metadata.get("separator_repr"),
        "sampling_method": read_metadata.get("sampling_method"),
        "columns": int(df.shape[1]),
        "duplicate_rows": int(df.duplicated().sum()),
        "duplicate_columns": duplicate_columns,
        "column_order": [str(c) for c in df.columns],
        "columns_detail": {},
        "possible_coordinate_pairs": [],
        "warnings": [],
        "hints": [],
    }

    if df.empty:
        profile["warnings"].append("table is empty")

    roles: dict[str, str] = {}
    for col in df.columns:
        series = df[col]
        role = infer_role(series, col)
        roles[str(col)] = role
        detail: dict[str, Any] = {
            "dtype": str(series.dtype),
            "role": role,
            "missing": int(series.isna().sum()),
            "missing_pct": round(float(series.isna().mean() * 100), 2),
            "unique": int(series.nunique(dropna=True)),
        }
        if role in {"categorical", "numeric-discrete", "year"}:
            counts = series.value_counts(dropna=True).head(max_categories)
            detail["top_counts"] = {str(k): int(v) for k, v in counts.items()}
        if role in {"numeric", "numeric-discrete", "proportion", "latitude", "longitude", "year"}:
            detail["numeric_summary"] = numeric_summary(series)
        if role == "identifier":
            detail["note"] = "identifier-like column; do not use as a numeric measure unless intended"
        if detail["missing_pct"] > 50:
            detail.setdefault("warnings", []).append("more than 50% missing")
        if role == "numeric-invalid":
            detail.setdefault("warnings", []).append("numeric dtype but no finite numeric values")
        profile["columns_detail"][str(col)] = detail

    profile["possible_coordinate_pairs"] = possible_coordinate_pairs(roles)

    numeric_roles = {"numeric", "proportion"}
    numeric_cols = [c for c, r in roles.items() if r in numeric_roles]
    cat_cols = [c for c, r in roles.items() if r in {"categorical", "numeric-discrete"}]
    time_cols = [c for c, r in roles.items() if r in {"datetime", "datetime-like", "year"}]
    id_cols = [c for c, r in roles.items() if r == "identifier"]

    if duplicate_columns:
        profile["warnings"].append(f"duplicate column names detected: {duplicate_columns}")
    if profile["duplicate_rows"]:
        profile["warnings"].append(f"duplicate rows detected: {profile['duplicate_rows']}")
    if id_cols:
        profile["hints"].append(f"Identifier-like columns detected and excluded from numeric chart hints: {id_cols[:6]}.")
    if profile["possible_coordinate_pairs"]:
        pair = profile["possible_coordinate_pairs"][0]
        profile["hints"].append(f"Map candidate: plot latitude/longitude using lon={pair['lon']} and lat={pair['lat']}.")
    if time_cols and numeric_cols:
        profile["hints"].append(
            f"Time/sequence candidate: line plot of {numeric_cols[:3]} over {time_cols[0]}."
        )
    if len(numeric_cols) >= 2:
        profile["hints"].append(
            f"Relationship candidate: scatter/density plot for numeric columns such as {numeric_cols[:2]}."
        )
    if cat_cols and numeric_cols:
        group = cat_cols[0]
        counts = df[group].value_counts(dropna=True)
        low_n = counts[counts < 10]
        hint = f"Group comparison candidate: raw points plus box/violin/interval for {numeric_cols[0]} by {group}."
        if not low_n.empty:
            hint += f" Low-n groups detected: {list(map(str, low_n.index[:6]))}."
        profile["hints"].append(hint)
    if len(numeric_cols) >= 4:
        profile["hints"].append("Matrix candidate: correlation heatmap; use a diverging scale centered at 0.")
    if not profile["hints"]:
        profile["hints"].append("No obvious chart family detected; inspect the intended message before plotting.")

    # Guard against non-standard JSON values.
    return json_sanitize(profile)


def json_sanitize(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): json_sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [json_sanitize(v) for v in obj]
    if isinstance(obj, tuple):
        return [json_sanitize(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        value = float(obj)
        return value if math.isfinite(value) else None
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    return obj


def parse_sheet(value: str | None) -> str | int | None:
    if value is None:
        return None
    if value.isdigit():
        return int(value)
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="CSV/TSV/TXT/Excel/Parquet file to profile")
    parser.add_argument("--json", type=Path, help="Optional JSON output path")
    parser.add_argument("--sep", default="auto", help="Delimiter for text files; default auto uses csv.Sniffer with an extension fallback")
    parser.add_argument("--encoding", help="Optional text-file encoding")
    parser.add_argument("--sheet", help="Excel sheet name or zero-based index")
    parser.add_argument("--max-categories", type=int, default=12, help="Maximum category counts to report per column")
    parser.add_argument(
        "--sample-rows",
        type=int,
        help="Profile only the first/head N rows; this is not random sampling",
    )
    args = parser.parse_args()
    if args.sample_rows is not None and args.sample_rows <= 0:
        parser.error("--sample-rows must be a positive integer")

    profile = build_profile(
        args.input,
        sep=args.sep,
        encoding=args.encoding,
        sheet=parse_sheet(args.sheet),
        max_categories=args.max_categories,
        sample_rows=args.sample_rows,
    )
    text = json.dumps(profile, ensure_ascii=False, indent=2, allow_nan=False)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(text, encoding="utf-8")
        print(f"wrote {args.json}")
    print(text)


if __name__ == "__main__":
    main()
