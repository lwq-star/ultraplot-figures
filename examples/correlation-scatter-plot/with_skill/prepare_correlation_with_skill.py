from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd


OUTPUT_DIR = Path(__file__).resolve().parent
SOURCE_WORKBOOK = OUTPUT_DIR.parent / "data" / "multiple_data.xlsx"
SHEET_NAME = "Sheet1"
LAND_COVERS = ("cropland", "forest", "grassland", "savanna")
MODELS = ("DNN", "GBRT", "LR", "SVR")

PAIRS_PATH = OUTPUT_DIR / "correlation_pairs_with_skill.csv"
STATS_PATH = OUTPUT_DIR / "correlation_stats_with_skill.csv"
AUDIT_PATH = OUTPUT_DIR / "data_audit_with_skill.json"


def report_relative_path(path: Path, report_path: Path) -> str:
    return Path(os.path.relpath(path, start=report_path.parent)).as_posix()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def expected_columns() -> list[str]:
    return [
        f"{land_cover}{model}_{suffix}"
        for land_cover in LAND_COVERS
        for model in MODELS
        for suffix in (0, 1)
    ]


def main() -> None:
    source_hash_before = sha256(SOURCE_WORKBOOK)
    workbook = pd.ExcelFile(SOURCE_WORKBOOK)
    if workbook.sheet_names != [SHEET_NAME]:
        raise ValueError(
            f"Expected exactly [{SHEET_NAME!r}], found {workbook.sheet_names!r}."
        )

    wide = pd.read_excel(SOURCE_WORKBOOK, sheet_name=SHEET_NAME)
    expected = expected_columns()
    if wide.columns.tolist() != expected:
        raise ValueError("Workbook columns or column order differ from expectation.")
    if not all(pd.api.types.is_numeric_dtype(wide[column]) for column in expected):
        raise TypeError("All 32 data columns must be numeric.")

    pair_frames: list[pd.DataFrame] = []
    stats_rows: list[dict[str, float | int | str]] = []
    land_cover_audit: dict[str, object] = {}

    for land_cover in LAND_COVERS:
        land_columns = [
            f"{land_cover}{model}_{suffix}"
            for model in MODELS
            for suffix in (0, 1)
        ]
        missing_masks = [wide[column].isna() for column in land_columns]
        aligned_missing = all(
            mask.equals(missing_masks[0]) for mask in missing_masks[1:]
        )
        if not aligned_missing:
            raise ValueError(
                f"Missing-value positions are not aligned for {land_cover}."
            )

        value_0_identical = all(
            wide[f"{land_cover}{MODELS[0]}_0"].equals(
                wide[f"{land_cover}{model}_0"]
            )
            for model in MODELS[1:]
        )
        if not value_0_identical:
            raise ValueError(
                f"_0 values are not identical across models for {land_cover}."
            )

        valid_index = np.flatnonzero(~missing_masks[0].to_numpy())
        valid_prefix = np.array_equal(valid_index, np.arange(valid_index.size))
        if not valid_prefix:
            raise ValueError(
                f"Missing rows are not a trailing padding block for {land_cover}."
            )

        land_cover_audit[land_cover] = {
            "paired_observations_per_model": int(valid_index.size),
            "trailing_padding_rows": int(len(wide) - valid_index.size),
            "missing_positions_aligned_across_all_8_columns": aligned_missing,
            "value_0_identical_across_models": value_0_identical,
            "valid_rows_form_contiguous_prefix": valid_prefix,
        }

        for model in MODELS:
            column_0 = f"{land_cover}{model}_0"
            column_1 = f"{land_cover}{model}_1"
            incomplete_pair = wide[column_0].isna() ^ wide[column_1].isna()
            if incomplete_pair.any():
                raise ValueError(
                    f"Found one-sided missing pairs in {column_0!r}/{column_1!r}."
                )

            valid = wide[[column_0, column_1]].notna().all(axis=1)
            pair = wide.loc[valid, [column_0, column_1]].rename(
                columns={column_0: "value_0", column_1: "value_1"}
            )
            pair.insert(0, "source_row", pair.index.to_numpy(dtype=int) + 2)
            pair.insert(0, "model", model)
            pair.insert(0, "land_cover", land_cover)

            x = pair["value_0"].to_numpy(dtype=float)
            y = pair["value_1"].to_numpy(dtype=float)
            if not (np.isfinite(x).all() and np.isfinite(y).all()):
                raise ValueError(f"Non-finite paired values found for {land_cover}/{model}.")
            if np.ptp(x) == 0 or np.ptp(y) == 0:
                raise ValueError(f"Constant series found for {land_cover}/{model}.")

            slope, intercept = np.polyfit(x, y, deg=1)
            stats_rows.append(
                {
                    "land_cover": land_cover,
                    "model": model,
                    "n": int(x.size),
                    "pearson_r": float(np.corrcoef(x, y)[0, 1]),
                    "ols_slope": float(slope),
                    "ols_intercept": float(intercept),
                    "x_min": float(x.min()),
                    "x_max": float(x.max()),
                    "y_min": float(y.min()),
                    "y_max": float(y.max()),
                }
            )
            pair_frames.append(pair)

    pairs = pd.concat(pair_frames, ignore_index=True)
    stats = pd.DataFrame(stats_rows)
    if pairs.duplicated(["land_cover", "model", "source_row"]).any():
        raise ValueError("Duplicate land-cover/model/source-row keys were generated.")

    pairs.to_csv(PAIRS_PATH, index=False, float_format="%.17g")
    stats.to_csv(STATS_PATH, index=False, float_format="%.17g")

    source_hash_after = sha256(SOURCE_WORKBOOK)
    if source_hash_after != source_hash_before:
        raise RuntimeError("Source workbook changed while it was being read.")

    audit = {
        "path_base": "directory_containing_this_json",
        "source_workbook": report_relative_path(SOURCE_WORKBOOK, AUDIT_PATH),
        "source_sha256_before_and_after": source_hash_before,
        "source_was_modified": False,
        "sheet_name": SHEET_NAME,
        "wide_shape": [int(value) for value in wide.shape],
        "columns": expected,
        "all_columns_numeric": True,
        "wide_duplicate_rows": int(wide.duplicated().sum()),
        "land_cover_checks": land_cover_audit,
        "processing": [
            "Reshaped the 32 wide columns into one row per finite paired observation.",
            "Removed only rows where both members of a pair were missing; these were validated as trailing padding.",
            "Retained the original Excel row number for traceability.",
            "Applied no filtering, clipping, winsorization, aggregation, imputation, or unit conversion.",
            "Calculated Pearson r and ordinary least-squares y-on-x coefficients for each panel.",
        ],
        "processed_pair_rows": int(len(pairs)),
        "statistics_rows": int(len(stats)),
        "units": None,
        "units_note": "No units were present in the workbook; none were invented.",
    }
    AUDIT_PATH.write_text(json.dumps(audit, indent=2), encoding="ascii")

    print(f"Wrote {PAIRS_PATH} ({len(pairs):,} paired rows)")
    print(f"Wrote {STATS_PATH} ({len(stats):,} panel summaries)")
    print(f"Wrote {AUDIT_PATH}")
    print(stats[["land_cover", "model", "n", "pearson_r"]].to_string(index=False))


if __name__ == "__main__":
    main()
