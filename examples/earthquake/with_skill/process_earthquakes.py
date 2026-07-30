"""Validate and prepare the 2025 global M >= 5 earthquake dataset."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import numpy as np


DEFAULT_INPUT = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "usgs_earthquakes_2025_m5plus.geojson"
)
TARGET_YEAR = 2025
MIN_MAGNITUDE = 5.0


def utc_iso(epoch_ms: int | float) -> str:
    value = dt.datetime.fromtimestamp(epoch_ms / 1000, tz=dt.timezone.utc)
    return value.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=fieldnames, lineterminator="\n", extrasaction="raise"
        )
        writer.writeheader()
        writer.writerows(rows)


def validate_geojson_provenance(document: dict) -> None:
    if document.get("type") != "FeatureCollection":
        raise ValueError("Expected a GeoJSON FeatureCollection.")

    metadata = document.get("metadata")
    if not isinstance(metadata, dict):
        raise ValueError("Missing USGS GeoJSON metadata object.")
    parsed = urlparse(str(metadata.get("url", "")))
    query = parse_qs(parsed.query)
    if parsed.hostname != "earthquake.usgs.gov":
        raise ValueError("Source provenance is not earthquake.usgs.gov.")
    if query.get("format") != ["geojson"]:
        raise ValueError("Source metadata does not identify a GeoJSON query.")
    if metadata.get("status") != 200:
        raise ValueError("Source metadata status is not 200.")

    explicit_crs = document.get("crs")
    if explicit_crs is not None:
        raise ValueError(
            "An explicit GeoJSON CRS member is present; manual CRS review is required."
        )

def parse_feature(feature: dict, index: int) -> dict:
    geometry = feature.get("geometry")
    properties = feature.get("properties")
    if not isinstance(geometry, dict) or geometry.get("type") != "Point":
        raise ValueError(f"Feature {index} is not a GeoJSON Point.")
    if not isinstance(properties, dict):
        raise ValueError(f"Feature {index} has no properties object.")

    coordinates = geometry.get("coordinates")
    if not isinstance(coordinates, list) or len(coordinates) != 3:
        raise ValueError(f"Feature {index} does not have [lon, lat, depth].")
    if not all(isinstance(value, (int, float)) for value in coordinates):
        raise ValueError(f"Feature {index} has a non-numeric coordinate.")

    longitude, latitude, depth = map(float, coordinates)
    if not -180.0 <= longitude <= 180.0:
        raise ValueError(f"Feature {index} longitude is outside [-180, 180].")
    if not -90.0 <= latitude <= 90.0:
        raise ValueError(f"Feature {index} latitude is outside [-90, 90].")
    if depth < 0.0:
        raise ValueError(
            f"Feature {index} has negative depth; the planned depth classes require review."
        )

    magnitude = properties.get("mag")
    epoch_ms = properties.get("time")
    event_type = properties.get("type")
    if not isinstance(magnitude, (int, float)):
        raise ValueError(f"Feature {index} has no numeric magnitude.")
    if not isinstance(epoch_ms, (int, float)):
        raise ValueError(f"Feature {index} has no numeric epoch time.")
    if not isinstance(event_type, str):
        raise ValueError(f"Feature {index} has no event type.")

    event_id = feature.get("id")
    if not isinstance(event_id, str) or not event_id:
        raise ValueError(f"Feature {index} has no event id.")

    timestamp = dt.datetime.fromtimestamp(epoch_ms / 1000, tz=dt.timezone.utc)
    return {
        "event_id": event_id,
        "time_ms": int(epoch_ms),
        "time_utc": utc_iso(epoch_ms),
        "year_utc": timestamp.year,
        "longitude_deg": longitude,
        "latitude_deg": latitude,
        "depth_km": depth,
        "magnitude": float(magnitude),
        "magnitude_type": properties.get("magType") or "",
        "event_type": event_type,
        "place": properties.get("place") or "",
        "network": properties.get("net") or "",
        "status": properties.get("status") or "",
    }


def retained_row(row: dict) -> tuple[bool, list[str]]:
    reasons = []
    if row["event_type"] != "earthquake":
        reasons.append("event_type_not_earthquake")
    if row["year_utc"] != TARGET_YEAR:
        reasons.append("utc_year_not_2025")
    if row["magnitude"] < MIN_MAGNITUDE:
        reasons.append("magnitude_below_5")
    return not reasons, reasons


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument(
        "--output-dir", type=Path, default=Path(__file__).resolve().parent
    )
    args = parser.parse_args()
    input_path = args.input.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    raw_bytes = input_path.read_bytes()
    document = json.loads(raw_bytes)
    validate_geojson_provenance(document)
    features = document.get("features")
    if not isinstance(features, list) or not features:
        raise ValueError("FeatureCollection is empty or malformed.")

    parsed_rows = [parse_feature(feature, index) for index, feature in enumerate(features)]
    event_ids = [row["event_id"] for row in parsed_rows]
    if len(event_ids) != len(set(event_ids)):
        raise ValueError("Duplicate event ids are present.")

    retained = []
    excluded = []
    exclusion_counts: dict[str, int] = {}
    for row in parsed_rows:
        keep, reasons = retained_row(row)
        if keep:
            retained.append(row)
        else:
            reason_text = ";".join(reasons)
            excluded.append(
                {
                    "event_id": row["event_id"],
                    "time_utc": row["time_utc"],
                    "event_type": row["event_type"],
                    "magnitude": row["magnitude"],
                    "depth_km": row["depth_km"],
                    "reason": reason_text,
                }
            )
            for reason in reasons:
                exclusion_counts[reason] = exclusion_counts.get(reason, 0) + 1

    retained.sort(key=lambda row: (row["time_ms"], row["event_id"]))
    excluded.sort(key=lambda row: (row["time_utc"], row["event_id"]))
    if not retained:
        raise ValueError("No earthquakes remain after filtering.")

    event_fields = [
        "event_id",
        "time_ms",
        "time_utc",
        "longitude_deg",
        "latitude_deg",
        "depth_km",
        "magnitude",
        "magnitude_type",
        "event_type",
        "place",
        "network",
        "status",
    ]
    event_rows = [{key: row[key] for key in event_fields} for row in retained]
    events_path = output_dir / "earthquakes_2025_m5plus_processed.csv"
    excluded_path = output_dir / "excluded_features.csv"
    write_csv(events_path, event_fields, event_rows)
    write_csv(
        excluded_path,
        ["event_id", "time_utc", "event_type", "magnitude", "depth_km", "reason"],
        excluded,
    )

    magnitudes = np.asarray([row["magnitude"] for row in retained], dtype=float)
    depths = np.asarray([row["depth_km"] for row in retained], dtype=float)
    threshold_tenths = range(
        int(round(MIN_MAGNITUDE * 10)), int(np.ceil(magnitudes.max() * 10)) + 1
    )
    exceedance_rows = [
        {
            "magnitude_threshold": threshold / 10,
            "event_count_ge_threshold": int(np.count_nonzero(magnitudes >= threshold / 10)),
        }
        for threshold in threshold_tenths
    ]
    exceedance_path = output_dir / "magnitude_exceedance.csv"
    write_csv(
        exceedance_path,
        ["magnitude_threshold", "event_count_ge_threshold"],
        exceedance_rows,
    )

    class_specs = [
        ("Shallow", "0 to <70 km", 0.0, 70.0),
        ("Intermediate", "70 to <300 km", 70.0, 300.0),
        ("Deep", ">=300 km", 300.0, None),
    ]
    depth_class_rows = []
    for class_name, range_label, lower, upper in class_specs:
        mask = depths >= lower
        if upper is not None:
            mask &= depths < upper
        class_depths = depths[mask]
        depth_class_rows.append(
            {
                "class_name": class_name,
                "range_label": range_label,
                "lower_bound_km": lower,
                "upper_bound_km": "" if upper is None else upper,
                "event_count": int(mask.sum()),
                "event_percent": float(100 * mask.mean()),
                "median_depth_km": float(np.median(class_depths)),
            }
        )
    if sum(row["event_count"] for row in depth_class_rows) != len(retained):
        raise RuntimeError("Depth classes do not exhaust the retained events.")
    depth_classes_path = output_dir / "depth_classes.csv"
    write_csv(
        depth_classes_path,
        [
            "class_name",
            "range_label",
            "lower_bound_km",
            "upper_bound_km",
            "event_count",
            "event_percent",
            "median_depth_km",
        ],
        depth_class_rows,
    )

    declared_bbox = document.get("bbox")
    if not isinstance(declared_bbox, list) or len(declared_bbox) != 6:
        raise ValueError("Expected a six-value source bbox [xmin, ymin, zmin, xmax, ymax, zmax].")
    observed_source_bbox = [
        min(row["longitude_deg"] for row in parsed_rows),
        min(row["latitude_deg"] for row in parsed_rows),
        min(row["depth_km"] for row in parsed_rows),
        max(row["longitude_deg"] for row in parsed_rows),
        max(row["latitude_deg"] for row in parsed_rows),
        max(row["depth_km"] for row in parsed_rows),
    ]
    if not np.allclose(declared_bbox, observed_source_bbox, atol=1e-9, rtol=0):
        raise ValueError("Declared source bbox does not match observed feature coordinates.")

    print(
        json.dumps(
            {
                "status": "ok",
                "source_features": len(parsed_rows),
                "retained_earthquakes": len(retained),
                "excluded_features": len(excluded),
                "exclusion_counts": exclusion_counts,
                "magnitude_range": [float(magnitudes.min()), float(magnitudes.max())],
                "depth_km_range": [float(depths.min()), float(depths.max())],
                "outputs": [
                    path.name
                    for path in [
                        events_path,
                        exceedance_path,
                        depth_classes_path,
                        excluded_path,
                    ]
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
