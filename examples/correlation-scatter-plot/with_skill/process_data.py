"""Validate and reshape the correlation workbook before plotting."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


LAND_COVERS = ("cropland", "forest", "grassland", "savanna")
MODELS = ("DNN", "GBRT", "LR", "SVR")
SHEET_NAME = "Sheet1"
DEFAULT_INPUT = (
    Path(__file__).resolve().parents[1] / "data" / "multiple_data.xlsx"
)
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent


def expected_columns() -> list[str]:
    return [
        f"{land}{model}_{suffix}"
        for land in LAND_COVERS
        for model in MODELS
        for suffix in (0, 1)
    ]


def compute_statistics(
    land_cover: str,
    model: str,
    source_rows: np.ndarray,
    x: np.ndarray,
    y: np.ndarray,
) -> dict[str, float | int | str]:
    pearson = stats.pearsonr(x, y)
    pearson_ci = pearson.confidence_interval(confidence_level=0.95)
    spearman = stats.spearmanr(x, y)
    regression = stats.linregress(x, y)
    residual = y - x
    return {
        "land_cover": land_cover,
        "model": model,
        "n": int(x.size),
        "first_source_excel_row": int(source_rows.min()),
        "last_source_excel_row": int(source_rows.max()),
        "pearson_r": float(pearson.statistic),
        "pearson_p": float(pearson.pvalue),
        "pearson_ci95_low": float(pearson_ci.low),
        "pearson_ci95_high": float(pearson_ci.high),
        "spearman_rho": float(spearman.statistic),
        "spearman_p": float(spearman.pvalue),
        "ols_slope": float(regression.slope),
        "ols_intercept": float(regression.intercept),
        "ols_r_squared": float(regression.rvalue**2),
        "mean_bias_y_minus_x": float(np.mean(residual)),
        "mae": float(np.mean(np.abs(residual))),
        "rmse": float(np.sqrt(np.mean(residual**2))),
        "x_min": float(np.min(x)),
        "x_max": float(np.max(x)),
        "y_min": float(np.min(y)),
        "y_max": float(np.max(y)),
    }


def process(input_path: Path, output_dir: Path) -> None:
    input_path = input_path.resolve(strict=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    workbook = pd.ExcelFile(input_path, engine="openpyxl")
    if workbook.sheet_names != [SHEET_NAME]:
        raise ValueError(
            f"Expected exactly [{SHEET_NAME!r}], found {workbook.sheet_names!r}."
        )
    raw = pd.read_excel(workbook, sheet_name=SHEET_NAME)

    expected = expected_columns()
    actual = [str(column) for column in raw.columns]
    if actual != expected:
        missing = [column for column in expected if column not in actual]
        unexpected = [column for column in actual if column not in expected]
        raise ValueError(
            "Workbook columns do not match the required schema. "
            f"Missing={missing!r}; unexpected={unexpected!r}; order_match=False."
        )

    numeric = raw.apply(pd.to_numeric, errors="coerce")
    coercion_failures = raw.notna() & numeric.isna()
    if bool(coercion_failures.to_numpy().any()):
        failures = {
            column: int(coercion_failures[column].sum())
            for column in actual
            if coercion_failures[column].any()
        }
        raise ValueError(f"Non-numeric non-missing cells detected: {failures!r}")

    values = numeric.to_numpy(dtype=float)
    nonfinite_nonmissing = np.isinf(values)
    if bool(nonfinite_nonmissing.any()):
        raise ValueError("Positive or negative infinity is not permitted.")

    source_excel_rows = np.arange(2, len(numeric) + 2, dtype=int)
    processed_parts: list[pd.DataFrame] = []
    statistics_rows: list[dict[str, float | int | str]] = []
    pair_audit: list[dict[str, float | int | str | bool]] = []
    land_cover_audit: dict[str, object] = {}

    for land_cover in LAND_COVERS:
        x_columns = [f"{land_cover}{model}_0" for model in MODELS]
        x_columns_equal = all(
            numeric[x_columns[0]].equals(numeric[column])
            for column in x_columns[1:]
        )
        valid_masks: list[np.ndarray] = []

        for model in MODELS:
            x_series = numeric[f"{land_cover}{model}_0"]
            y_series = numeric[f"{land_cover}{model}_1"]
            x_missing = x_series.isna().to_numpy()
            y_missing = y_series.isna().to_numpy()
            complete = ~(x_missing | y_missing)
            valid_masks.append(complete)

            valid_indices = np.flatnonzero(complete)
            if valid_indices.size < 3:
                raise ValueError(
                    f"{land_cover}/{model} has fewer than three complete pairs."
                )
            internal_missing = int((~complete[: valid_indices[-1] + 1]).sum())

            x = x_series.to_numpy(dtype=float)[complete]
            y = y_series.to_numpy(dtype=float)[complete]
            rows = source_excel_rows[complete]
            processed_parts.append(
                pd.DataFrame(
                    {
                        "source_sheet": SHEET_NAME,
                        "source_excel_row": rows,
                        "land_cover": land_cover,
                        "model": model,
                        "value_0": x,
                        "value_1": y,
                    }
                )
            )
            statistics_rows.append(
                compute_statistics(land_cover, model, rows, x, y)
            )
            pair_audit.append(
                {
                    "land_cover": land_cover,
                    "model": model,
                    "source_rows": int(len(numeric)),
                    "complete_pairs": int(complete.sum()),
                    "missing_value_0": int(x_missing.sum()),
                    "missing_value_1": int(y_missing.sum()),
                    "missing_both": int((x_missing & y_missing).sum()),
                    "one_sided_missing": int((x_missing ^ y_missing).sum()),
                    "internal_missing_before_last_valid_row": internal_missing,
                    "first_valid_source_excel_row": int(rows.min()),
                    "last_valid_source_excel_row": int(rows.max()),
                }
            )

        land_cover_audit[land_cover] = {
            "value_0_columns_exactly_equal_across_models": x_columns_equal,
            "complete_pair_masks_exactly_equal_across_models": all(
                np.array_equal(valid_masks[0], mask) for mask in valid_masks[1:]
            ),
            "complete_pairs_per_model": int(valid_masks[0].sum()),
        }

    inconsistent_land_covers = [
        land_cover
        for land_cover, checks in land_cover_audit.items()
        if not checks["value_0_columns_exactly_equal_across_models"]
        or not checks["complete_pair_masks_exactly_equal_across_models"]
    ]
    if inconsistent_land_covers:
        raise ValueError(
            "Cross-model pairing assumptions failed for: "
            f"{inconsistent_land_covers!r}"
        )

    processed = pd.concat(processed_parts, ignore_index=True)
    statistics_frame = pd.DataFrame(statistics_rows)
    exclusion_frame = pd.DataFrame(pair_audit)

    processed_path = output_dir / "processed_pairs.csv"
    statistics_path = output_dir / "correlation_statistics.csv"
    exclusions_path = output_dir / "exclusion_summary.csv"

    expected_groups = len(LAND_COVERS) * len(MODELS)
    if len(statistics_frame) != expected_groups or len(exclusion_frame) != expected_groups:
        raise RuntimeError("Expected one statistics and exclusion row per data group.")
    if len(processed) != int(exclusion_frame["complete_pairs"].sum()):
        raise RuntimeError("Processed-row count does not match complete-pair counts.")

    processed.to_csv(
        processed_path, index=False, float_format="%.15g", lineterminator="\n"
    )
    statistics_frame.to_csv(
        statistics_path, index=False, float_format="%.15g", lineterminator="\n"
    )
    exclusion_frame.to_csv(exclusions_path, index=False, lineterminator="\n")

    print(f"Processed rows: {len(processed):,}")
    print(f"Statistics rows: {len(statistics_frame):,}")
    print(f"Wrote: {processed_path.name}")
    print(f"Wrote: {statistics_path.name}")
    print(f"Wrote: {exclusions_path.name}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    process(arguments.input, arguments.output_dir)
